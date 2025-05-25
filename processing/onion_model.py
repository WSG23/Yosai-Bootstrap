import pandas as pd
from scipy.stats import mode as scipy_mode
from collections import Counter
import numpy as np
import traceback

# Import other necessary functions from your project structure
# Ensure this import path is correct
from processing.cytoscape_prep import prepare_path_visualization_data 
from constants import REQUIRED_INTERNAL_COLUMNS # Needed for constants like EventType display name

# --- Helper Data Cleaning and Feature Engineering Functions ---

def normalize_door_ids(df, door_id_col='DoorID'):
    print(f"\nCleaning: Normalizing Door IDs in column '{door_id_col}'...")
    if door_id_col not in df.columns:
        print(f"Warning: Door ID column '{door_id_col}' not found for normalization. Available columns: {df.columns.tolist()}")
        return df
    df[door_id_col] = df[door_id_col].astype(str).str.upper().str.strip()
    df[door_id_col] = df[door_id_col].str.replace(r'\s+', ' ', regex=True)
    return df

def remove_rapid_same_door_scans(df, user_id_col='UserID', door_id_col='DoorID',
                                 timestamp_col='Timestamp', time_threshold_seconds=10):
    print(f"\nCleaning: Removing rapid scans on the same door (threshold: {time_threshold_seconds}s)...")
    if not all(col in df.columns for col in [user_id_col, door_id_col, timestamp_col]):
        print(f"Warning: One or more required columns ({user_id_col}, {door_id_col}, {timestamp_col}) not found for rapid scan removal. Available columns: {df.columns.tolist()}")
        return df
    if df.empty: return df
    
    # Ensure timestamp column is datetime type
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
        df.dropna(subset=[timestamp_col], inplace=True)
        if df.empty: return df # Check again after dropping NaNs

    df_sorted = df.sort_values(by=[user_id_col, door_id_col, timestamp_col]).copy()
    time_diff = df_sorted.groupby([user_id_col, door_id_col], group_keys=False)[timestamp_col].diff()
    mask_to_keep = (time_diff.isna()) | (time_diff > pd.Timedelta(seconds=time_threshold_seconds))
    df_cleaned = df_sorted[mask_to_keep].copy()
    print(f"Removed {len(df_sorted) - len(df_cleaned)} rapid same-door scans.")
    return df_cleaned.reset_index(drop=True)

def flag_ping_pong_scans(df, user_id_col='UserID', door_id_col='DoorID',
                         timestamp_col='Timestamp', ping_pong_threshold_minutes=1,
                         flag_column_name='IsPingPongAffected'):
    print(f"\nCleaning: Flagging ping-pong scans (A->B->A within {ping_pong_threshold_minutes} mins)...")
    if not all(col in df.columns for col in [user_id_col, door_id_col, timestamp_col]):
        print(f"Warning: One or more required columns ({user_id_col}, {door_id_col}, {timestamp_col}) not found for ping-pong flagging. Available columns: {df.columns.tolist()}")
        if flag_column_name not in df.columns: df[flag_column_name] = False
        return df
    if df.empty:
        if flag_column_name not in df.columns: df[flag_column_name] = False
        return df
    
    # Ensure timestamp column is datetime type
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
        df.dropna(subset=[timestamp_col], inplace=True)
        if df.empty: return df # Check again after dropping NaNs


    df_sorted = df.sort_values(by=[user_id_col, timestamp_col]).reset_index(drop=True)
    df_sorted[flag_column_name] = False
    flagged_indices_in_sorted_df = []
    
    # Group by user and process sequences
    for _, group in df_sorted.groupby(user_id_col, sort=False):
        if len(group) < 3: continue
        
        # Optimized loop for sequence checking
        door_ids = group[door_id_col].tolist()
        timestamps = group[timestamp_col].tolist()
        original_indices = group.index.tolist()

        for i in range(len(group) - 2):
            door1, door2, door3 = door_ids[i], door_ids[i+1], door_ids[i+2]
            time1, time3 = timestamps[i], timestamps[i+2]

            if door1 == door3 and door1 != door2:
                if (time3 - time1) <= pd.Timedelta(minutes=ping_pong_threshold_minutes):
                    flagged_indices_in_sorted_df.extend([original_indices[i], original_indices[i+1], original_indices[i+2]])
    
    if flagged_indices_in_sorted_df:
        unique_flagged_indices = sorted(list(set(flagged_indices_in_sorted_df)))
        df_sorted.loc[unique_flagged_indices, flag_column_name] = True
        print(f"Flagged {len(unique_flagged_indices)} events involved in ping-pong sequences.")
    return df_sorted

def process_user_day_events(group, timestamp_col='Timestamp (Event Time)',
                            depth_col='DeviceDepthPerDay', event_type_col='EventType_UserDay'):
    group = group.sort_values(timestamp_col).copy()
    group[depth_col] = range(1, len(group) + 1)
    if event_type_col not in group.columns: group[event_type_col] = ''
    if not group.empty:
        if len(group) == 1: group.loc[group.index[0], event_type_col] = 'ENTRANCE_EXIT'
        else:
            group.loc[group.index[0], event_type_col] = 'ENTRANCE'
            group.loc[group.index[-1], event_type_col] = 'EXIT'
            if len(group) > 2: group.loc[group.index[1:-1], event_type_col] = 'MOVEMENT'
    return group

def determine_heuristic_entrances(df, user_id_col='UserID (Person Identifier)', date_col='Date',
                                  door_id_col='DoorID (Device Name)', timestamp_col='Timestamp (Event Time)', top_n_entrances=5):
    print(f"\nDetermining heuristic entrances (top {top_n_entrances})...")
    if not all(col in df.columns for col in [user_id_col, date_col, door_id_col, timestamp_col]):
        print(f"Warning: Missing required columns ({user_id_col}, {date_col}, {door_id_col}, {timestamp_col}) for heuristic entrance determination. Available columns: {df.columns.tolist()}")
        return []
    if df.empty: return []
    try:
        # Ensure 'Date' column exists and is suitable for groupby, if not, try to derive it
        if date_col not in df.columns and timestamp_col in df.columns:
            print(f"Warning: '{date_col}' not found, deriving from '{timestamp_col}'.")
            df[date_col] = df[timestamp_col].dt.date
        elif date_col not in df.columns:
             print(f"Error: Cannot derive '{date_col}', '{timestamp_col}' column also missing.")
             return []

        first_event_indices = df.groupby([user_id_col, date_col], group_keys=False, observed=False)[timestamp_col].idxmin()
        first_events_df = df.loc[first_event_indices].copy() # Use .copy() to avoid SettingWithCopyWarning
        entrance_counts = first_events_df[door_id_col].value_counts()
        heuristic_entrance_list = entrance_counts.nlargest(top_n_entrances).index.tolist()
        print(f"Heuristic official entrances: {heuristic_entrance_list}")
        return heuristic_entrance_list
    except Exception as e:
        print(f"Error in determine_heuristic_entrances: {e}")
        traceback.print_exc()
        return []


def flag_unexpected_entry_points(df, official_entrance_door_ids, door_id_col='DoorID (Device Name)',
                                 event_type_user_day_col='EventType_UserDay', flag_column_name='IsUnexpectedEntry'):
    print("\nFlagging unexpected entry points...")
    if not all(col in df.columns for col in [door_id_col, event_type_user_day_col]):
        print(f"Warning: One or more required columns ({door_id_col}, {event_type_user_day_col}) not found for unexpected entry flagging. Available columns: {df.columns.tolist()}")
        if flag_column_name not in df.columns: df[flag_column_name] = False
        return df
    if flag_column_name not in df.columns: df[flag_column_name] = False
    if not official_entrance_door_ids:
        print("Warning: List of official entrance door IDs is empty for unexpected entry flagging.")
        return df
    standardized_official_entrances = {str(d_id).upper().strip() for d_id in official_entrance_door_ids}
    entrance_event_mask = df[event_type_user_day_col].isin(['ENTRANCE', 'ENTRANCE_EXIT'])
    
    # Ensure door_id_col is string for comparison
    df[door_id_col] = df[door_id_col].astype(str)
    condition_unexpected_entry = entrance_event_mask & \
                                 (~df[door_id_col].str.upper().str.strip().isin(standardized_official_entrances))
    
    df.loc[condition_unexpected_entry, flag_column_name] = True
    print(f"Flagged {df[flag_column_name].sum()} events as unexpected entries.")
    return df

def calculate_final_global_device_depths(enriched_event_df, official_entrance_door_ids,
                                         door_id_col='DoorID (Device Name)', device_depth_per_day_col='DeviceDepthPerDay'):
    print("\nCalculating Final Global Device Depths...")
    if enriched_event_df.empty or device_depth_per_day_col not in enriched_event_df.columns or door_id_col not in enriched_event_df.columns:
        print(f"Warning: Enriched DataFrame is empty or missing '{device_depth_per_day_col}' or '{door_id_col}'.")
        # Return empty DataFrame with all expected columns for graceful failure
        return pd.DataFrame(columns=[door_id_col, 'FinalGlobalDeviceDepth', 'IsOfficialEntrance', 'IsGloballyCritical', 'MostCommonNextDoor', 'Floor', 'IsStaircase', 'SecurityLevel'])

    def get_mode_robust(series): # Nested helper
        series_cleaned = pd.to_numeric(series, errors='coerce').dropna()
        if series_cleaned.empty: return pd.Series([None, 0], index=['mode', 'count'])
        try: # Added try-except for robustness in scipy_mode call
            m = scipy_mode(series_cleaned, keepdims=False) # keepdims=False to avoid array return for scalar mode
            mode_val, count_val = None, 0
            if hasattr(m, 'mode'): mode_val = m.mode if np.isscalar(m.mode) else (m.mode[0] if m.mode.size > 0 else None)
            if hasattr(m, 'count'): count_val = m.count if np.isscalar(m.count) else (m.count[0] if m.count.size > 0 else 0)
            
            if mode_val is None: return pd.Series([None, 0], index=['mode', 'count'])
            mode_val = int(float(mode_val)) # Ensure integer conversion
            count_val = int(float(count_val)) # Ensure integer conversion
            return pd.Series([mode_val, count_val], index=['mode', 'count'])
        except Exception as e:
            print(f"Error in get_mode_robust: {e}")
            return pd.Series([None, 0], index=['mode', 'count'])

    standardized_official_entrances = {str(d_id).upper().strip() for d_id in official_entrance_door_ids}
    
    # Ensure DoorID is string type for comparison
    enriched_event_df[door_id_col] = enriched_event_df[door_id_col].astype(str)

    all_devices_in_events = enriched_event_df[door_id_col].unique()
    device_layer_info_list = []
    
    non_entrance_devices_df = enriched_event_df[~enriched_event_df[door_id_col].isin(standardized_official_entrances)].copy()
    provisional_depths_non_entrances = pd.DataFrame(columns=[door_id_col, 'ProvisionalGlobalDeviceDepth', 'ModeCount'])

    if not non_entrance_devices_df.empty and device_depth_per_day_col in non_entrance_devices_df.columns:
        grouped_modes = non_entrance_devices_df.groupby(door_id_col, group_keys=False, observed=False)[device_depth_per_day_col]
        if grouped_modes.ngroups > 0:
            temp_modes_df = grouped_modes.apply(get_mode_robust).reset_index()
            if 'mode' in temp_modes_df.columns and 'count' in temp_modes_df.columns:
                temp_modes_df.rename(columns={'mode': 'ProvisionalGlobalDeviceDepth', 'count': 'ModeCount'}, inplace=True)
                temp_modes_df['ProvisionalGlobalDeviceDepth'] = pd.to_numeric(temp_modes_df['ProvisionalGlobalDeviceDepth'], errors='coerce')
                temp_modes_df.dropna(subset=['ProvisionalGlobalDeviceDepth'], inplace=True)
                if temp_modes_df['ProvisionalGlobalDeviceDepth'].notna().all():
                     temp_modes_df['ProvisionalGlobalDeviceDepth'] = temp_modes_df['ProvisionalGlobalDeviceDepth'].astype(int)
                provisional_depths_non_entrances = temp_modes_df
            else: print(f"Warning: 'mode' or 'count' column missing after apply in provisional depths. Columns: {temp_modes_df.columns.tolist()}")
        else:
            print("No groups found for provisional depth calculation.")
    else:
        print("Non-entrance devices DataFrame is empty or missing required column for provisional depth calculation.")
    
    for device_id in all_devices_in_events:
        is_official_entrance = device_id in standardized_official_entrances
        final_depth = 1 if is_official_entrance else -2 # Default -2 for error/unassigned non-entrance
        if not is_official_entrance:
            device_mode_info = provisional_depths_non_entrances[provisional_depths_non_entrances[door_id_col] == device_id]
            if not device_mode_info.empty and 'ProvisionalGlobalDeviceDepth' in device_mode_info.columns:
                prov_depth_scalar = device_mode_info['ProvisionalGlobalDeviceDepth'].iloc[0]
                if pd.notna(prov_depth_scalar): final_depth = int(prov_depth_scalar) + 1
                else: final_depth = -1 # Fallback marker for NaN provisional depth
            else: final_depth = -1 # Fallback marker if not in precalculated modes
            
            if final_depth == -1 or final_depth == -2: # Fallback logic for unassigned
                # Assign a default non-entrance depth, e.g., 99 or a value indicating "unknown interior"
                final_depth = 99 
                print(f"Info: Device '{device_id}' using fallback depth {final_depth} (was -1 or -2).")


        device_layer_info_list.append({
            door_id_col: device_id, 'FinalGlobalDeviceDepth': final_depth,
            'IsOfficialEntrance': is_official_entrance})
            
    final_device_layers_df = pd.DataFrame(device_layer_info_list)
    print(f"DEBUG: Final device layers DataFrame size: {len(final_device_layers_df)} rows. Columns: {final_device_layers_df.columns.tolist()}")
    return final_device_layers_df

def add_globally_critical_flag(device_layers_df, door_id_col='DoorID (Device Name)', depth_col='FinalGlobalDeviceDepth',
                               entrance_col='IsOfficialEntrance', critical_flag_col='IsGloballyCritical'):
    print("\nIdentifying Globally Critical Devices...")
    if device_layers_df.empty or depth_col not in device_layers_df.columns or entrance_col not in device_layers_df.columns or door_id_col not in device_layers_df.columns:
        print(f"Warning: Device layers DataFrame is unsuitable for critical device identification. Missing one or more of '{door_id_col}', '{depth_col}', '{entrance_col}'. Columns: {device_layers_df.columns.tolist()}")
        if critical_flag_col not in device_layers_df.columns : device_layers_df[critical_flag_col] = False
        return device_layers_df
    if critical_flag_col not in device_layers_df.columns: device_layers_df[critical_flag_col] = False
    
    # Filter for non-entrances with a valid depth (greater than 0)
    non_entrances_df = device_layers_df[
        (~device_layers_df[entrance_col]) &
        (device_layers_df[depth_col].notna()) & # Ensure depth is not NaN
        (device_layers_df[depth_col] > 0)
    ].copy()

    if not non_entrances_df.empty:
        max_depth_non_entrances = non_entrances_df[depth_col].max()
        if pd.notna(max_depth_non_entrances):
            critical_mask = (~device_layers_df[entrance_col]) & \
                            (device_layers_df[depth_col] == max_depth_non_entrances)
            device_layers_df.loc[critical_mask, critical_flag_col] = True
            print(f"Flagged {device_layers_df[critical_flag_col].sum()} devices as globally critical.")
    else:
        print("No non-entrance devices with valid depth found to identify globally critical devices.")
    
    print(f"DEBUG: Device layers after critical flag: {device_layers_df.columns.tolist()}")
    return device_layers_df

def find_most_common_next_doors(enriched_event_df, user_id_col='UserID (Person Identifier)', date_col='Date',
                                timestamp_col='Timestamp (Event Time)', door_id_col='DoorID (Device Name)'):
    print("\nFinding Most Common Next Doors...")
    if enriched_event_df.empty:
        print("Enriched event DataFrame is empty for finding common next doors.")
        return pd.DataFrame(columns=['SourceDoor', 'TargetDoor', 'TransitionFrequency']), \
               pd.DataFrame(columns=['SourceDoor', 'MostCommonNextDoor', 'FrequencyOfMostCommon'])
    
    if not all(col in enriched_event_df.columns for col in [user_id_col, date_col, timestamp_col, door_id_col]):
        print(f"Warning: Missing required columns for finding most common next doors. Columns: {enriched_event_df.columns.tolist()}")
        return pd.DataFrame(columns=['SourceDoor', 'TargetDoor', 'TransitionFrequency']), \
               pd.DataFrame(columns=['SourceDoor', 'MostCommonNextDoor', 'FrequencyOfMostCommon'])


    df_sorted = enriched_event_df.sort_values(by=[user_id_col, date_col, timestamp_col]).copy()
    
    # Ensure DoorID is string type for comparison
    df_sorted[door_id_col] = df_sorted[door_id_col].astype(str)

    # Shift to get the next door for each user/day sequence
    df_sorted['NextDoor'] = df_sorted.groupby([user_id_col, date_col], group_keys=False)[door_id_col].shift(-1)
    
    transitions_df = df_sorted.dropna(subset=['NextDoor']).copy()
    transitions_df.rename(columns={door_id_col: 'SourceDoor', 'NextDoor': 'TargetDoor'}, inplace=True)
    
    if transitions_df.empty:
        print("No transitions found after identifying next doors.")
        return pd.DataFrame(columns=['SourceDoor', 'TargetDoor', 'TransitionFrequency']), \
               pd.DataFrame(columns=['SourceDoor', 'MostCommonNextDoor', 'FrequencyOfMostCommon'])
    
    # Calculate transition frequencies
    path_frequencies = transitions_df.groupby(['SourceDoor', 'TargetDoor'], observed=False).size().reset_index(name='TransitionFrequency')
    path_frequencies = path_frequencies.sort_values(by=['SourceDoor', 'TransitionFrequency'], ascending=[True, False])
    
    most_common_next = pd.DataFrame(columns=['SourceDoor', 'MostCommonNextDoor', 'FrequencyOfMostCommon'])
    if not path_frequencies.empty:
        idx = path_frequencies.groupby(['SourceDoor'], group_keys=False, observed=False)['TransitionFrequency'].idxmax()
        most_common_next = path_frequencies.loc[idx].copy()
        most_common_next.rename(columns={'TargetDoor': 'MostCommonNextDoor', 'TransitionFrequency': 'FrequencyOfMostCommon'}, inplace=True)
    else:
        print("Path frequencies DataFrame is empty.")

    print(f"DEBUG: Found {len(path_frequencies)} unique transitions.")
    print(f"DEBUG: Found {len(most_common_next)} most common next doors.")

    # Initialize 'is_to_inner_default' column if it's expected later
    # This might be specific to prepare_path_visualization_data. Let's add it here
    # Assuming 'is_to_inner_default' is for all_paths_df, which is what path_frequencies becomes.
    if 'is_to_inner_default' not in path_frequencies.columns:
        path_frequencies['is_to_inner_default'] = False # Default value
        
    return path_frequencies, most_common_next


# --- Main Processing Orchestrator ---
def run_onion_model_processing(raw_df, config_params, confirmed_official_entrances=None, detailed_door_classifications=None):
    print("\n--- Starting Onion Model Data Processing Pipeline ---")
    if raw_df is None or raw_df.empty:
        print("Error: Input DataFrame to pipeline is empty or None. Exiting pipeline.")
        cols_dev_attrs = ['DoorID (Device Name)', 'FinalGlobalDeviceDepth', 'IsOfficialEntrance', 'IsGloballyCritical', 'MostCommonNextDoor', 'Floor', 'IsStaircase', 'SecurityLevel']
        cols_path_viz = ['SourceDoor', 'TargetDoor', 'PathWidth'] # Renamed Door1/Door2 to Source/Target for consistency
        cols_all_paths = ['SourceDoor', 'TargetDoor', 'TransitionFrequency', 'is_to_inner_default']
        return raw_df, pd.DataFrame(columns=cols_dev_attrs), pd.DataFrame(columns=cols_path_viz), pd.DataFrame(columns=cols_all_paths)

    processed_df = raw_df.copy()
    print(f"DEBUG: Initial DataFrame size: {len(processed_df)} rows.")

    # Define display names once at the top of the function for clarity
    TIMESTAMP_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['Timestamp']
    USERID_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['UserID']
    DOORID_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['DoorID']
    EVENTTYPE_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['EventType']
    DATE_COL_NAME = 'Date' # This is an internal name, derived within the pipeline

    # Module 1 Steps (Data Cleaning, Initial Feature Engineering)
    print("\n--- Module 1: Initial Event Filtering & Feature Engineering ---")
    
    # EventType Filtering
    if EVENTTYPE_COL_DISPLAY not in processed_df.columns:
        print(f"Error: '{EVENTTYPE_COL_DISPLAY}' column missing for filtering. Skipping EventType filter.")
    else:
        initial_len = len(processed_df)
        processed_df[EVENTTYPE_COL_DISPLAY] = processed_df[EVENTTYPE_COL_DISPLAY].astype(str)

        primary_indicator = config_params.get('primary_positive_indicator', "ACCESS GRANTED").upper()
        processed_df = processed_df[processed_df[EVENTTYPE_COL_DISPLAY].str.upper().str.contains(primary_indicator)].copy()
        print(f"DEBUG: After '{primary_indicator}' filter: {len(processed_df)} rows. Removed {initial_len - len(processed_df)}.")
        initial_len = len(processed_df) 

        for phrase in config_params.get('invalid_phrases_exact', ["INVALID ACCESS LEVEL"]):
            processed_df = processed_df[~(processed_df[EVENTTYPE_COL_DISPLAY].str.upper() == phrase.upper())].copy()
            print(f"DEBUG: After exact filter '{phrase}': {len(processed_df)} rows. Removed {initial_len - len(processed_df)}.")
            initial_len = len(processed_df)

        for phrase in config_params.get('invalid_phrases_contain', ["NO ENTRY MADE"]):
            processed_df = processed_df[~(processed_df[EVENTTYPE_COL_DISPLAY].str.upper().str.contains(phrase.upper()))].copy()
            print(f"DEBUG: After contains filter '{phrase}': {len(processed_df)} rows. Removed {initial_len - len(processed_df)}.")
            initial_len = len(processed_df)

    if processed_df.empty:
        print("No events after initial event type filtering. Exiting pipeline.")
        return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    processed_df = normalize_door_ids(processed_df, door_id_col=DOORID_COL_DISPLAY)
    
    initial_len = len(processed_df)
    processed_df = remove_rapid_same_door_scans(processed_df,
                                                 user_id_col=USERID_COL_DISPLAY, 
                                                 door_id_col=DOORID_COL_DISPLAY, 
                                                 timestamp_col=TIMESTAMP_COL_DISPLAY, 
                                                 time_threshold_seconds=config_params.get('same_door_scan_threshold_seconds', 10))
    print(f"DEBUG: After rapid same-door scans removal: {len(processed_df)} rows. Removed {initial_len - len(processed_df)}.")
    if processed_df.empty: print("No events after rapid scan removal. Exiting pipeline."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    initial_len = len(processed_df)
    processed_df = flag_ping_pong_scans(processed_df,
                                        user_id_col=USERID_COL_DISPLAY, 
                                        door_id_col=DOORID_COL_DISPLAY, 
                                        timestamp_col=TIMESTAMP_COL_DISPLAY, 
                                        ping_pong_threshold_minutes=config_params.get('ping_pong_threshold_minutes', 1))
    if 'IsPingPongAffected' in processed_df.columns:
        num_flagged = processed_df['IsPingPongAffected'].sum()
        processed_df = processed_df[~processed_df['IsPingPongAffected']].copy()
        print(f"DEBUG: Removed {num_flagged} ping-pong affected events. Current rows: {len(processed_df)}.")
    if processed_df.empty: print("No events after ping-pong removal. Exiting pipeline."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Ensure timestamp column (display name) is datetime type
    if TIMESTAMP_COL_DISPLAY not in processed_df.columns:
        print(f"Error: '{TIMESTAMP_COL_DISPLAY}' column missing for timestamp processing. Exiting pipeline.")
        return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    if not pd.api.types.is_datetime64_any_dtype(processed_df[TIMESTAMP_COL_DISPLAY]):
        print(f"DEBUG: Converting '{TIMESTAMP_COL_DISPLAY}' to datetime.")
        processed_df[TIMESTAMP_COL_DISPLAY] = pd.to_datetime(processed_df[TIMESTAMP_COL_DISPLAY], errors='coerce')
        initial_len = len(processed_df)
        processed_df.dropna(subset=[TIMESTAMP_COL_DISPLAY], inplace=True) # Drop rows where timestamp conversion failed
        print(f"DEBUG: After Timestamp NaN drop: {len(processed_df)} rows. Removed {initial_len - len(processed_df)}.")
    if processed_df.empty: print("No events after timestamp cleaning. Exiting pipeline."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


    # Ensure 'Date' column exists, deriving from Timestamp (display name)
    if DATE_COL_NAME not in processed_df.columns: 
        if TIMESTAMP_COL_DISPLAY in processed_df.columns:
            print(f"DEBUG: Deriving '{DATE_COL_NAME}' from '{TIMESTAMP_COL_DISPLAY}'.")
            processed_df[DATE_COL_NAME] = processed_df[TIMESTAMP_COL_DISPLAY].dt.date
        else:
            print(f"Error: Neither '{DATE_COL_NAME}' nor '{TIMESTAMP_COL_DISPLAY}' found to derive date. Exiting pipeline.")
            return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Calculate DeviceDepthPerDay and EventType_UserDay
    req_cols_daily = [USERID_COL_DISPLAY, DATE_COL_NAME, TIMESTAMP_COL_DISPLAY]
    if not all(col in processed_df.columns for col in req_cols_daily):
        print(f"Error: Missing one of {req_cols_daily} for daily processing. Exiting pipeline."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    processed_df.sort_values(by=req_cols_daily, inplace=True)
    grouped_events = processed_df.groupby([USERID_COL_DISPLAY, DATE_COL_NAME], group_keys=False, observed=False)
    
    if grouped_events.ngroups > 0:
        enriched_event_df = grouped_events.apply(lambda g: process_user_day_events(g, timestamp_col=TIMESTAMP_COL_DISPLAY))
        print(f"DEBUG: After daily event processing (DeviceDepthPerDay, EventType_UserDay): {len(enriched_event_df)} rows.")
    else:
        enriched_event_df = processed_df.copy() # If no groups, use as is but ensure columns
        if 'DeviceDepthPerDay' not in enriched_event_df.columns: enriched_event_df['DeviceDepthPerDay'] = 0
        if 'EventType_UserDay' not in enriched_event_df.columns: enriched_event_df['EventType_UserDay'] = ''
        print("No user-date groups found for depth/event type classification, or DataFrame was empty before apply. Using processed_df as enriched_event_df.")
    
    if enriched_event_df.empty: print("DataFrame empty after daily processing. Exiting pipeline."); return enriched_event_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Determine and use official entrances
    if confirmed_official_entrances is not None and len(confirmed_official_entrances) > 0:
        official_entrance_door_ids = [str(d).upper().strip() for d in confirmed_official_entrances]
        print(f"\nUsing USER-CONFIRMED official entrances: {official_entrance_door_ids}")
    else:
        print("\nWarning: No user-confirmed entrances. Falling back to heuristic.")
        official_entrance_door_ids = determine_heuristic_entrances(
            enriched_event_df,
            user_id_col=USERID_COL_DISPLAY,
            date_col=DATE_COL_NAME,
            door_id_col=DOORID_COL_DISPLAY,
            timestamp_col=TIMESTAMP_COL_DISPLAY,
            top_n_entrances=config_params.get('top_n_heuristic_entrances', 3)
        )
    
    enriched_event_df = flag_unexpected_entry_points(enriched_event_df, official_entrance_door_ids,
                                                     door_id_col=DOORID_COL_DISPLAY) 
    print("Module 1 (Initial Processing & Feature Engineering) Complete.")
    print(f"DEBUG: Enriched DataFrame size before Module 2: {len(enriched_event_df)} rows.")

    # Module 2 Steps (Core Onion Layer Generation)
    device_attributes_df = calculate_final_global_device_depths(
        enriched_event_df, official_entrance_door_ids,
        door_id_col=DOORID_COL_DISPLAY, 
        device_depth_per_day_col='DeviceDepthPerDay' # This remains internal
    )
    if device_attributes_df.empty or \
       ('FinalGlobalDeviceDepth' in device_attributes_df.columns and (device_attributes_df['FinalGlobalDeviceDepth'] < 0).any()) or \
       DOORID_COL_DISPLAY not in device_attributes_df.columns: 
        print("Warning or Error in global depths. Re-creating basic device_attributes_df.")
        all_devs = enriched_event_df[DOORID_COL_DISPLAY].unique() if DOORID_COL_DISPLAY in enriched_event_df.columns else []
        device_attributes_df = pd.DataFrame({
            DOORID_COL_DISPLAY: all_devs, 
            'FinalGlobalDeviceDepth': 1, # Fallback depth
            'IsOfficialEntrance': [str(d).upper().strip() in official_entrance_door_ids for d in all_devs]
        })
    
    if 'IsGloballyCritical' not in device_attributes_df.columns:
        device_attributes_df['IsGloballyCritical'] = False 
    device_attributes_df = add_globally_critical_flag(device_attributes_df,
                                                       door_id_col=DOORID_COL_DISPLAY) 
    print("Module 2 (Core Layer Generation) Complete.")
    print(f"DEBUG: Device Attributes DataFrame size: {len(device_attributes_df)} rows. Columns: {device_attributes_df.columns.tolist()}")


    # Module 3 Steps ("Yellow Door" Placement Logic)
    all_paths_df, most_common_paths_df = find_most_common_next_doors(
        enriched_event_df,
        user_id_col=USERID_COL_DISPLAY, 
        date_col=DATE_COL_NAME,
        timestamp_col=TIMESTAMP_COL_DISPLAY, 
        door_id_col=DOORID_COL_DISPLAY 
    )
    if DOORID_COL_DISPLAY in device_attributes_df.columns and not most_common_paths_df.empty:
        device_attributes_df = pd.merge(device_attributes_df, most_common_paths_df[['SourceDoor', 'MostCommonNextDoor']],
                                        left_on=DOORID_COL_DISPLAY, right_on='SourceDoor', how='left')
        if 'SourceDoor' in device_attributes_df.columns: device_attributes_df.drop(columns=['SourceDoor'], inplace=True)
    if 'MostCommonNextDoor' not in device_attributes_df.columns: 
        device_attributes_df['MostCommonNextDoor'] = pd.NA
    print("Module 3 (Most Common Next Door) Complete.")
    print(f"DEBUG: All Paths DataFrame size: {len(all_paths_df) if all_paths_df is not None else 'None'}")
    print(f"DEBUG: Most Common Paths DataFrame size: {len(most_common_paths_df) if most_common_paths_df is not None else 'None'}")

    # --- Integration of detailed_door_classifications (floor, is_stair, security_level) ---
    if detailed_door_classifications and not device_attributes_df.empty and DOORID_COL_DISPLAY in device_attributes_df.columns:
        manual_attrs_df = pd.DataFrame.from_dict(detailed_door_classifications, orient='index')
        manual_attrs_df.index.name = 'DoorID_manual' 
        manual_attrs_df.reset_index(inplace=True) 
        
        manual_attrs_df.rename(columns={
            'DoorID_manual': DOORID_COL_DISPLAY, 
            'floor': 'Floor',
            'is_stair': 'IsStaircase',
            'security': 'SecurityLevel',
            'is_ee': 'IsManuallyEE' 
        }, inplace=True)

        cols_to_merge = [DOORID_COL_DISPLAY]
        for col in ['Floor', 'IsStaircase', 'SecurityLevel', 'IsManuallyEE']:
            if col in manual_attrs_df.columns:
                cols_to_merge.append(col)
        
        if len(cols_to_merge) > 1:
            original_index_name = device_attributes_df.index.name
            if DOORID_COL_DISPLAY in device_attributes_df.columns:
                device_attributes_df_indexed = device_attributes_df.set_index(DOORID_COL_DISPLAY)
                manual_attrs_df_indexed = manual_attrs_df.set_index(DOORID_COL_DISPLAY)
                
                for col in manual_attrs_df_indexed.columns:
                    if col in device_attributes_df_indexed.columns:
                        device_attributes_df_indexed[col].update(manual_attrs_df_indexed[col])
                    else:
                        device_attributes_df_indexed[col] = manual_attrs_df_indexed[col]
                
                device_attributes_df = device_attributes_df_indexed.reset_index()
                if original_index_name: 
                    device_attributes_df.set_index(original_index_name, inplace=True)

            print("Merged detailed door classifications into device_attributes_df.")
    
    expected_device_cols = [DOORID_COL_DISPLAY, 'FinalGlobalDeviceDepth', 'IsOfficialEntrance',
                            'IsGloballyCritical', 'MostCommonNextDoor', 'Floor', 
                            'IsStaircase', 'SecurityLevel']
    for col in expected_device_cols:
        if col not in device_attributes_df.columns:
            if col == 'Floor': device_attributes_df[col] = '1' 
            elif col in ['IsOfficialEntrance', 'IsGloballyCritical', 'IsStaircase']: device_attributes_df[col] = False 
            else: device_attributes_df[col] = pd.NA 

    # Module 4 Steps (Path Visualization Prep)
    # Ensure all_paths_df is not None/empty before passing it.
    if all_paths_df is not None and not all_paths_df.empty:
        path_viz_data_df = prepare_path_visualization_data(all_paths_df) 
    else:
        print("Warning: all_paths_df is empty or None, skipping path visualization prep.")
        path_viz_data_df = pd.DataFrame(columns=['SourceDoor', 'TargetDoor', 'PathWidth']) # Return empty dataframe

    print("Module 4 (Path Visualization Data Prep) Complete.")
    
    print("\n--- All Data Processing Pipeline Complete ---")
    print(f"DEBUG: Final enriched_event_df rows: {len(enriched_event_df) if enriched_event_df is not None else 'None'}")
    print(f"DEBUG: Final device_attributes_df rows: {len(device_attributes_df) if device_attributes_df is not None else 'None'}")
    print(f"DEBUG: Final path_viz_data_df rows: {len(path_viz_data_df) if path_viz_data_df is not None else 'None'}")
    print(f"DEBUG: Final all_paths_df rows: {len(all_paths_df) if all_paths_df is not None else 'None'}")

    return enriched_event_df, device_attributes_df, path_viz_data_df, all_paths_df