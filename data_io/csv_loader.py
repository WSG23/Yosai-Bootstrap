import pandas as pd
import io
import base64 # Not used directly in this function but often in the calling Dash callback
import traceback
from constants import REQUIRED_INTERNAL_COLUMNS

def load_csv_event_log(csv_file_obj, column_mapping, timestamp_format=None):
    """
    Loads event log data from a CSV file (or StringIO object) with flexible column mapping.
    csv_file_obj: Can be a file path or an io.StringIO object.
    column_mapping: A dictionary like {'Original CSV Header': 'Standardized Name'}
    (where 'Standardized Name' should be the display name, e.g., 'Timestamp (Event Time)')
    """
    print(f"Attempting to load CSV data.")
    try:
        # pandas read_csv can handle both file paths and StringIO objects
        df = pd.read_csv(csv_file_obj, dtype=str)

        # Validate that all source columns in the mapping exist in the CSV
        for source_col in column_mapping.keys():
            if source_col not in df.columns:
                print(f"Error: Source column '{source_col}' (mapped to '{column_mapping.get(source_col)}') not found in the CSV. Available columns: {df.columns.tolist()}")
                return None

        standardized_data = {}
        for source_col, standard_name in column_mapping.items():
            if source_col in df.columns: # Ensure column exists before trying to access
                standardized_data[standard_name] = df[source_col]
            # else: This case implies an optional mapping or an error already caught

        event_df = pd.DataFrame(standardized_data)

        # Validate that all essential standardized columns (display names) are present
        # REQUIRED_INTERNAL_COLUMNS.values() holds the display names (e.g., 'Timestamp (Event Time)')
        for req_display_col in REQUIRED_INTERNAL_COLUMNS.values(): 
            if req_display_col not in event_df.columns:
                 # Find the internal key that maps to req_display_col for a better error message
                target_internal_key_for_error = "Unknown"
                for k,v in REQUIRED_INTERNAL_COLUMNS.items():
                    if v == req_display_col:
                        target_internal_key_for_error = k
                        break
                print(f"Error: Standard column '{req_display_col}' (expected for internal key '{target_internal_key_for_error}') is missing after initial mapping. DataFrame columns: {event_df.columns.tolist()}")
                return None
        
        # ✅ REMOVED THE FOLLOWING LINES:
        # # Rename columns to the internal keys used by the rest of the application
        # # e.g., 'Timestamp (Event Time)' becomes 'Timestamp'
        # reverse_rename_map = {v: k for k, v in REQUIRED_INTERNAL_COLUMNS.items()}
        # event_df.rename(columns=reverse_rename_map, inplace=True)


        # Now, event_df columns are expected to be the 'Display Names'
        # Adjust subsequent checks and operations to use display names
        TIMESTAMP_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['Timestamp']
        DOORID_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['DoorID']
        USERID_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['UserID']
        EVENTTYPE_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['EventType']


        if TIMESTAMP_COL_DISPLAY not in event_df.columns: 
            print(f"Error: Display column '{TIMESTAMP_COL_DISPLAY}' is missing after mapping.")
            return None

        if timestamp_format:
            event_df[TIMESTAMP_COL_DISPLAY] = pd.to_datetime(event_df[TIMESTAMP_COL_DISPLAY], format=timestamp_format, errors='coerce')
        else:
            event_df[TIMESTAMP_COL_DISPLAY] = pd.to_datetime(event_df[TIMESTAMP_COL_DISPLAY], errors='coerce')

        event_df.dropna(subset=[TIMESTAMP_COL_DISPLAY], inplace=True)
        
        # Ensure other key columns are of correct type
        for col_display_name in [DOORID_COL_DISPLAY, USERID_COL_DISPLAY, EVENTTYPE_COL_DISPLAY]:
            if col_display_name in event_df.columns:
                event_df[col_display_name] = event_df[col_display_name].astype(str)
            else:
                print(f"Warning: Display column '{col_display_name}' missing after processing.")


        print(f"Successfully loaded and standardized {len(event_df)} events. Final columns: {event_df.columns.tolist()}")
        return event_df

    except FileNotFoundError: # This applies if csv_file_obj was a path string
        print(f"Error: The file was not found.") 
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading CSV: {e}")
        traceback.print_exc()
        return None