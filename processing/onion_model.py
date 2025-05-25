# yosai_intel_dashboard/processing/onion_model.py
import pandas as pd
from scipy.stats import mode as scipy_mode
from collections import Counter # Not explicitly used in the final version of these functions, but good to keep if any sub-logic might evolve
import numpy as np
import traceback # For robust error handling in get_mode_robust

# Import other necessary functions from your project structure
from processing.cytoscape_prep import prepare_path_visualization_data # If you keep it separate

# --- Helper Data Cleaning and Feature Engineering Functions ---
def normalize_door_ids(df, door_id_col='DoorID'):
    print(f"\nCleaning: Normalizing Door IDs in column '{door_id_col}'...")
    if door_id_col not in df.columns:
        print(f"Warning: Door ID column '{door_id_col}' not found for normalization.")
        return df
    df[door_id_col] = df[door_id_col].astype(str).str.upper().str.strip()
    df[door_id_col] = df[door_id_col].str.replace(r'\s+', ' ', regex=True)
    return df

def remove_rapid_same_door_scans(df, user_id_col='UserID', door_id_col='DoorID',
                                 timestamp_col='Timestamp', time_threshold_seconds=10):
    print(f"\nCleaning: Removing rapid scans on the same door (threshold: {time_threshold_seconds}s)...")
    if not all(col in df.columns for col in [user_id_col, door_id_col, timestamp_col]):
        print(f"Warning: One or more required columns not found for rapid scan removal.")
        return df
    if df.empty: return df
    df_sorted = df.sort_values(by=[user_id_col, door_id_col, timestamp_col])
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
        print("Warning: One or more required columns not found for ping-pong flagging.")
        if flag_column_name not in df.columns: df[flag_column_name] = False
        return df
    if df.empty:
        if flag_column_name not in df.columns: df[flag_column_name] = False
        return df
    df_sorted = df.sort_values(by=[user_id_col, timestamp_col]).reset_index(drop=True)
    df_sorted[flag_column_name] = False
    flagged_indices_in_sorted_df = []
    for _, group in df_sorted.groupby(user_id_col, sort=False):
        if len(group) < 3: continue
        i = 0
        while i <= len(group) - 3:
            event1_idx, event2_idx, event3_idx = group.index[i], group.index[i+1], group.index[i+2]
            door1, door2, door3 = group.iloc[i][door_id_col], group.iloc[i+1][door_id_col], group.iloc[i+2][door_id_col]
            time1, time3 = group.iloc[i][timestamp_col], group.iloc[i+2][timestamp_col]
            if door1 == door3 and door1 != door2:
                if (time3 - time1) <= pd.Timedelta(minutes=ping_pong_threshold_minutes):
                    flagged_indices_in_sorted_df.extend([event1_idx, event2_idx, event3_idx])
                    i += 2 # Advance past this full sequence
            i += 1
    if flagged_indices_in_sorted_df:
        unique_flagged_indices = sorted(list(set(flagged_indices_in_sorted_df)))
        df_sorted.loc[unique_flagged_indices, flag_column_name] = True
        print(f"Flagged {len(unique_flagged_indices)} events involved in ping-pong sequences.")
    return df_sorted

def process_user_day_events(group, timestamp_col='Timestamp',
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

def determine_heuristic_entrances(df, user_id_col='UserID', date_col='Date',
                                  door_id_col='DoorID', timestamp_col='Timestamp', top_n_entrances=5):
    print(f"\nDetermining heuristic entrances (top {top_n_entrances})...")
    if not all(col in df.columns for col in [user_id_col, date_col, door_id_col, timestamp_col]):
        print("Warning: Missing required columns for heuristic entrance determination.")
        return []
    if df.empty: return []
    try:
        # Ensure 'Date' column exists and is suitable for groupby, if not, try to derive it
        if date_col not in df.columns and timestamp_col in df.columns:
            print(f"Warning: '{date_col}' not found, deriving from '{timestamp_col}'.")
            df[date_col] = df[timestamp_col].dt.date

        first_event_indices = df.groupby([user_id_col, date_col], group_keys=False, observed=False)[timestamp_col].idxmin()
        first_events_df = df.loc[first_event_indices]
        entrance_counts = first_events_df[door_id_col].value_counts()
        heuristic_entrance_list = entrance_counts.nlargest(top_n_entrances).index.tolist()
        print(f"Heuristic official entrances: {heuristic_entrance_list}")
        return heuristic_entrance_list
    except Exception as e:
        print(f"Error in determine_heuristic_entrances: {e}")
        traceback.print_exc()
        return []


def flag_unexpected_entry_points(df, official_entrance_door_ids, door_id_col='DoorID',
                                 event_type_user_day_col='EventType_UserDay', flag_column_name='IsUnexpectedEntry'):
    print("\nFlagging unexpected entry points...")
    if not all(col in df.columns for col in [door_id_col, event_type_user_day_col]):
        print("Warning: One or more required columns not found for unexpected entry flagging.")
        if flag_column_name not in df.columns: df[flag_column_name] = False
        return df
    if flag_column_name not in df.columns: df[flag_column_name] = False
    if not official_entrance_door_ids:
        print("Warning: List of official entrance door IDs is empty.")
        return df
    standardized_official_entrances = {str(d_id).upper().strip() for d_id in official_entrance_door_ids}
    entrance_event_mask = df[event_type_user_day_col].isin(['ENTRANCE', 'ENTRANCE_EXIT'])
    condition_unexpected_entry = entrance_event_mask & \
                                 (~df[door_id_col].astype(str).str.upper().str.strip().isin(standardized_official_entrances))
    df.loc[condition_unexpected_entry, flag_column_name] = True
    print(f"Flagged {df[flag_column_name].sum()} events as unexpected entries.")
    return df

def calculate_final_global_device_depths(enriched_event_df, official_entrance_door_ids,
                                         door_id_col='DoorID', device_depth_per_day_col='DeviceDepthPerDay'):
    print("\nCalculating Final Global Device Depths...")
    if enriched_event_df.empty or device_depth_per_day_col not in enriched_event_df.columns:
        print(f"Warning: Enriched DataFrame is empty or missing '{device_depth_per_day_col}'.")
        return pd.DataFrame(columns=[door_id_col, 'FinalGlobalDeviceDepth', 'IsOfficialEntrance'])

    def get_mode_robust(series): # Nested helper
        series_cleaned = pd.to_numeric(series, errors='coerce').dropna()
        if series_cleaned.empty: return pd.Series([None, 0], index=['mode', 'count'])
        m = scipy_mode(series_cleaned)
        mode_val, count_val = None, 0
        if hasattr(m, 'mode'):
            if np.isscalar(m.mode): mode_val = m.mode
            elif isinstance(m.mode, np.ndarray) and m.mode.size > 0: mode_val = m.mode[0]
        if hasattr(m, 'count'):
            if np.isscalar(m.count): count_val = m.count
            elif isinstance(m.count, np.ndarray) and m.count.size > 0: count_val = m.count[0]
        if mode_val is None: return pd.Series([None, 0], index=['mode', 'count'])
        try: mode_val = int(float(mode_val))
        except: return pd.Series([None, 0], index=['mode', 'count']) # Error converting mode
        try: count_val = int(float(count_val))
        except: count_val = 0 # Default count on error
        return pd.Series([mode_val, count_val], index=['mode', 'count'])

    standardized_official_entrances = {str(d_id).upper().strip() for d_id in official_entrance_door_ids}
    all_devices_in_events = enriched_event_df[door_id_col].unique()
    device_layer_info_list = []
    
    non_entrance_devices_df = enriched_event_df[~enriched_event_df[door_id_col].isin(standardized_official_entrances)]
    provisional_depths_non_entrances = pd.DataFrame(columns=[door_id_col, 'ProvisionalGlobalDeviceDepth', 'ModeCount'])

    if not non_entrance_devices_df.empty:
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
            else: print(f"Warning: 'mode' or 'count' column missing after apply. Columns: {temp_modes_df.columns}")
    
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
            
            if final_depth == -1: # Fallback logic
                # (Simplified fallback: assign a high number or based on individual mode)
                # Your original fallback logic was more complex, ensure it's robustly transcribed if fully needed
                final_depth = 99 # Example simple fallback
                print(f"Info: Device '{device_id}' using fallback depth {final_depth}.")


        device_layer_info_list.append({
            door_id_col: device_id, 'FinalGlobalDeviceDepth': final_depth,
            'IsOfficialEntrance': is_official_entrance})
            
    final_device_layers_df = pd.DataFrame(device_layer_info_list)
    return final_device_layers_df

def add_globally_critical_flag(device_layers_df, door_id_col='DoorID', depth_col='FinalGlobalDeviceDepth',
                               entrance_col='IsOfficialEntrance', critical_flag_col='IsGloballyCritical'):
    print("\nIdentifying Globally Critical Devices...")
    if device_layers_df.empty or depth_col not in device_layers_df.columns or entrance_col not in device_layers_df.columns:
        print("Warning: Device layers DataFrame is unsuitable for critical device identification.")
        if critical_flag_col not in device_layers_df.columns : device_layers_df[critical_flag_col] = False
        return device_layers_df
    if critical_flag_col not in device_layers_df.columns: device_layers_df[critical_flag_col] = False
    non_entrances_df = device_layers_df[(~device_layers_df[entrance_col]) & (device_layers_df[depth_col] > 0)]
    if not non_entrances_df.empty:
        max_depth_non_entrances = non_entrances_df[depth_col].max()
        if pd.notna(max_depth_non_entrances):
            critical_mask = (~device_layers_df[entrance_col]) & (device_layers_df[depth_col] == max_depth_non_entrances)
            device_layers_df.loc[critical_mask, critical_flag_col] = True
            print(f"Flagged {device_layers_df[critical_flag_col].sum()} devices as globally critical.")
    return device_layers_df

def find_most_common_next_doors(enriched_event_df, user_id_col='UserID', date_col='Date',
                                timestamp_col='Timestamp', door_id_col='DoorID'):
    print("\nFinding Most Common Next Doors...")
    if enriched_event_df.empty:
        return pd.DataFrame(columns=['SourceDoor', 'TargetDoor', 'TransitionFrequency']), \
               pd.DataFrame(columns=['SourceDoor', 'MostCommonNextDoor', 'FrequencyOfMostCommon'])
    df_sorted = enriched_event_df.sort_values(by=[user_id_col, date_col, timestamp_col])
    df_sorted['NextDoor'] = df_sorted.groupby([user_id_col, date_col], group_keys=False)[door_id_col].shift(-1)
    transitions_df = df_sorted.dropna(subset=['NextDoor']).copy()
    transitions_df.rename(columns={door_id_col: 'SourceDoor', 'NextDoor': 'TargetDoor'}, inplace=True)
    if transitions_df.empty:
        return pd.DataFrame(columns=['SourceDoor', 'TargetDoor', 'TransitionFrequency']), \
               pd.DataFrame(columns=['SourceDoor', 'MostCommonNextDoor', 'FrequencyOfMostCommon'])
    path_frequencies = transitions_df.groupby(['SourceDoor', 'TargetDoor'], observed=False).size().reset_index(name='TransitionFrequency')
    path_frequencies = path_frequencies.sort_values(by=['SourceDoor', 'TransitionFrequency'], ascending=[True, False])
    if path_frequencies.empty:
        most_common_next = pd.DataFrame(columns=['SourceDoor', 'MostCommonNextDoor', 'FrequencyOfMostCommon'])
    else:
        idx = path_frequencies.groupby(['SourceDoor'], group_keys=False, observed=False)['TransitionFrequency'].idxmax()
        most_common_next = path_frequencies.loc[idx].copy()
        most_common_next.rename(columns={'TargetDoor': 'MostCommonNextDoor', 'TransitionFrequency': 'FrequencyOfMostCommon'}, inplace=True)
    return path_frequencies, most_common_next


# --- Main Processing Orchestrator ---
def run_onion_model_processing(raw_df, config_params, confirmed_official_entrances=None, detailed_door_classifications=None):
    print("Starting Onion Model Data Processing Pipeline...")
    if raw_df is None or raw_df.empty:
        print("Error: Input DataFrame to pipeline is empty or None.")
        # Return empty DataFrames with expected columns for graceful failure
        cols_dev_attrs = ['DoorID', 'FinalGlobalDeviceDepth', 'IsOfficialEntrance', 'IsGloballyCritical', 'MostCommonNextDoor', 'Floor', 'IsStaircase', 'SecurityLevel']
        cols_path_viz = ['Door1', 'Door2', 'PathWidth']
        cols_all_paths = ['SourceDoor', 'TargetDoor', 'TransitionFrequency', 'is_to_inner_default']
        return raw_df, pd.DataFrame(columns=cols_dev_attrs), pd.DataFrame(columns=cols_path_viz), pd.DataFrame(columns=cols_all_paths)

    processed_df = raw_df.copy()

    # Module 1 Steps (Data Cleaning, Initial Feature Engineering)
    print("\n--- Module 1: Initial Event Filtering & Feature Engineering ---")
    if 'EventType' not in processed_df.columns:
        print(f"Error: 'EventType' column missing for filtering.")
        # Potentially return or handle error, for now, continue if other steps don't rely exclusively on it
    else:
        processed_df = processed_df[processed_df['EventType'].astype(str).str.upper().str.contains(config_params.get('primary_positive_indicator', "ACCESS GRANTED").upper())].copy()
        for phrase in config_params.get('invalid_phrases_exact', ["INVALID ACCESS LEVEL"]):
            processed_df = processed_df[~(processed_df['EventType'].astype(str).str.upper() == phrase.upper())].copy()
        for phrase in config_params.get('invalid_phrases_contain', ["NO ENTRY MADE"]): # Typo fixed from "contaign"
            processed_df = processed_df[~(processed_df['EventType'].astype(str).str.upper().str.contains(phrase.upper()))].copy()
    
    if processed_df.empty: print("No events after initial event type filtering."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    processed_df = normalize_door_ids(processed_df) # Uses 'DoorID' default
    processed_df = remove_rapid_same_door_scans(processed_df, time_threshold_seconds=config_params.get('same_door_scan_threshold_seconds', 10))
    processed_df = flag_ping_pong_scans(processed_df, ping_pong_threshold_minutes=config_params.get('ping_pong_threshold_minutes', 1))
    if 'IsPingPongAffected' in processed_df.columns:
        num_flagged = processed_df['IsPingPongAffected'].sum()
        processed_df = processed_df[~processed_df['IsPingPongAffected']].copy()
        print(f"Removed {num_flagged} ping-pong affected events.")
    if processed_df.empty: print("No events after ping-pong removal."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if 'Timestamp' not in processed_df.columns: print("Error: Timestamp column missing."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    if not pd.api.types.is_datetime64_any_dtype(processed_df['Timestamp']):
        processed_df['Timestamp'] = pd.to_datetime(processed_df['Timestamp'], errors='coerce')
        processed_df.dropna(subset=['Timestamp'], inplace=True) # Drop rows where timestamp conversion failed

    if 'Date' not in processed_df.columns: # Ensure Date column exists
        processed_df['Date'] = processed_df['Timestamp'].dt.date

    # Calculate DeviceDepthPerDay and EventType_UserDay
    req_cols_daily = ['UserID', 'Date', 'Timestamp']
    if not all(col in processed_df.columns for col in req_cols_daily):
        print(f"Error: Missing one of {req_cols_daily} for daily processing."); return processed_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    processed_df.sort_values(by=req_cols_daily, inplace=True)
    grouped_events = processed_df.groupby(['UserID', 'Date'], group_keys=False, observed=False)
    if grouped_events.ngroups > 0:
        enriched_event_df = grouped_events.apply(lambda g: process_user_day_events(g))
    else:
        enriched_event_df = processed_df.copy() # If no groups, use as is but ensure columns
        if 'DeviceDepthPerDay' not in enriched_event_df.columns: enriched_event_df['DeviceDepthPerDay'] = 0
        if 'EventType_UserDay' not in enriched_event_df.columns: enriched_event_df['EventType_UserDay'] = ''
        print("No user-date groups found for depth/event type classification, or DataFrame was empty before apply.")
    if enriched_event_df.empty: print("DataFrame empty after daily processing."); return enriched_event_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Determine and use official entrances
    if confirmed_official_entrances is not None and len(confirmed_official_entrances) > 0:
        official_entrance_door_ids = [str(d).upper().strip() for d in confirmed_official_entrances]
        print(f"\nUsing USER-CONFIRMED official entrances: {official_entrance_door_ids}")
    else:
        print("\nWarning: No user-confirmed entrances. Falling back to heuristic.")
        official_entrance_door_ids = determine_heuristic_entrances(enriched_event_df, top_n_entrances=config_params.get('top_n_heuristic_entrances', 3)) # Default 3 from your test
    
    enriched_event_df = flag_unexpected_entry_points(enriched_event_df, official_entrance_door_ids)
    print("Module 1 (Initial Processing & Feature Engineering) Complete.")

    # Module 2 Steps (Core Onion Layer Generation)
    device_attributes_df = calculate_final_global_device_depths(enriched_event_df, official_entrance_door_ids)
    if device_attributes_df.empty or \
       ('FinalGlobalDeviceDepth' in device_attributes_df.columns and (device_attributes_df['FinalGlobalDeviceDepth'] < 0).any()) or \
       'DoorID' not in device_attributes_df.columns: # Check if DoorID is missing
        print("Warning or Error in global depths. Re-creating basic device_attributes_df.")
        all_devs = enriched_event_df['DoorID'].unique() if 'DoorID' in enriched_event_df else []
        device_attributes_df = pd.DataFrame({
            'DoorID': all_devs,
            'FinalGlobalDeviceDepth': 1, # Fallback depth
            'IsOfficialEntrance': [str(d).upper().strip() in official_entrance_door_ids for d in all_devs]
        })
    
    # Ensure critical flag column exists before calling add_globally_critical_flag
    if 'IsGloballyCritical' not in device_attributes_df.columns:
        device_attributes_df['IsGloballyCritical'] = False # Initialize if missing
    device_attributes_df = add_globally_critical_flag(device_attributes_df)
    print("Module 2 (Core Layer Generation) Complete.")

    # Module 3 Steps ("Yellow Door" Placement Logic)
    all_paths_df, most_common_paths_df = find_most_common_next_doors(enriched_event_df)
    if 'DoorID' in device_attributes_df.columns and not most_common_paths_df.empty:
        device_attributes_df = pd.merge(device_attributes_df, most_common_paths_df[['SourceDoor', 'MostCommonNextDoor']],
                                        left_on='DoorID', right_on='SourceDoor', how='left')
        if 'SourceDoor' in device_attributes_df.columns: device_attributes_df.drop(columns=['SourceDoor'], inplace=True)
    if 'MostCommonNextDoor' not in device_attributes_df.columns: # Ensure column exists
        device_attributes_df['MostCommonNextDoor'] = pd.NA
    print("Module 3 (Most Common Next Door) Complete.")

    # --- Integration of detailed_door_classifications (floor, is_stair, security_level) ---
    if detailed_door_classifications and not device_attributes_df.empty and 'DoorID' in device_attributes_df.columns:
        manual_attrs_df = pd.DataFrame.from_dict(detailed_door_classifications, orient='index')
        manual_attrs_df.index.name = 'DoorID_manual' # Temp name to avoid clash if 'DoorID' is a column
        manual_attrs_df.reset_index(inplace=True) # Make DoorID_manual a column
        
        # Standardize column names from manual_attrs_df if they are different from expected
        # Expected: 'floor', 'is_stair', 'security' (from callback)
        # Target in device_attributes_df: 'Floor', 'IsStaircase', 'SecurityLevel'
        manual_attrs_df.rename(columns={
            'DoorID_manual': 'DoorID', # for merging
            'floor': 'Floor',
            'is_stair': 'IsStaircase',
            'security': 'SecurityLevel',
            'is_ee': 'IsManuallyEE' # Keep manual E/E status if needed, IsOfficialEntrance is already set
        }, inplace=True)

        # Select only relevant columns for merge to avoid duplicating others
        cols_to_merge = ['DoorID']
        for col in ['Floor', 'IsStaircase', 'SecurityLevel', 'IsManuallyEE']:
            if col in manual_attrs_df.columns:
                cols_to_merge.append(col)
        
        if len(cols_to_merge) > 1: # If there's more than just DoorID
            # Merge, preferring values from manual_attrs_df if columns already exist from processing
            # To do this, update device_attributes_df with values from manual_attrs_df
            # This requires DoorID to be the index for easy update/combine_first
            
            # Store original index if it's not DoorID
            original_index_name = device_attributes_df.index.name
            if 'DoorID' in device_attributes_df.columns:
                device_attributes_df_indexed = device_attributes_df.set_index('DoorID')
                manual_attrs_df_indexed = manual_attrs_df.set_index('DoorID')
                
                # Update existing columns, add new ones
                for col in manual_attrs_df_indexed.columns:
                    if col in device_attributes_df_indexed.columns:
                        device_attributes_df_indexed[col].update(manual_attrs_df_indexed[col])
                    else:
                        device_attributes_df_indexed[col] = manual_attrs_df_indexed[col]
                
                device_attributes_df = device_attributes_df_indexed.reset_index()
                # Restore original index if necessary (though usually not for this df)
                if original_index_name:
                    device_attributes_df.set_index(original_index_name, inplace=True)

            print("Merged detailed door classifications into device_attributes_df.")
    
    # Ensure all expected columns are present in device_attributes_df for cytoscape_prep
    expected_device_cols = ['DoorID', 'FinalGlobalDeviceDepth', 'IsOfficialEntrance',
                            'IsGloballyCritical', 'MostCommonNextDoor', 'Floor', 
                            'IsStaircase', 'SecurityLevel']
    for col in expected_device_cols:
        if col not in device_attributes_df.columns:
            if col == 'Floor': device_attributes_df[col] = '1' # Default floor
            elif col in ['IsOfficialEntrance', 'IsGloballyCritical', 'IsStaircase']: device_attributes_df[col] = False # Default boolean
            else: device_attributes_df[col] = pd.NA # Default for others like MostCommonNextDoor, SecurityLevel

    # Module 4 Steps (Path Visualization Prep)
    path_viz_data_df = prepare_path_visualization_data(all_paths_df) # Call from cytoscape_prep
    print("Module 4 (Path Visualization Data Prep) Complete.")
    
    print("\nAll Data Processing Pipeline Complete.")
    return enriched_event_df, device_attributes_df, path_viz_data_df, all_paths_df