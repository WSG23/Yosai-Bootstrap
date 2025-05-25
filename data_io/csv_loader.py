# yosai_intel_dashboard/data_io/csv_loader.py
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

        # Validate that all essential standardized columns are present
        # REQUIRED_INTERNAL_COLUMNS defines the *target* standardized names
        for req_std_col in REQUIRED_INTERNAL_COLUMNS.values(): # Check against the values (standardized names)
            if req_std_col not in event_df.columns:
                 # Find the key in REQUIRED_INTERNAL_COLUMNS that maps to req_std_col for a better error message
                target_key_for_error = "Unknown"
                for k,v in REQUIRED_INTERNAL_COLUMNS.items():
                    if v == req_std_col:
                        target_key_for_error = k
                        break
                print(f"Error: Standard column '{req_std_col}' (expected for internal key '{target_key_for_error}') is missing after mapping. DataFrame columns: {event_df.columns.tolist()}")
                return None
        
        # Rename columns to the internal keys used by the rest of the application
        # e.g., 'Timestamp (Event Time)' becomes 'Timestamp'
        reverse_rename_map = {v: k for k, v in REQUIRED_INTERNAL_COLUMNS.items()}
        event_df.rename(columns=reverse_rename_map, inplace=True)


        if 'Timestamp' not in event_df.columns: # Check after renaming
            print(f"Error: Internal 'Timestamp' column is missing after mapping and renaming.")
            return None

        if timestamp_format:
            event_df['Timestamp'] = pd.to_datetime(event_df['Timestamp'], format=timestamp_format, errors='coerce')
        else:
            event_df['Timestamp'] = pd.to_datetime(event_df['Timestamp'], errors='coerce')

        event_df.dropna(subset=['Timestamp'], inplace=True)
        
        # Ensure other key columns are of correct type
        for col_key in ['DoorID', 'UserID', 'EventType']:
            if col_key in event_df.columns:
                event_df[col_key] = event_df[col_key].astype(str)
            else:
                print(f"Warning: Internal key column '{col_key}' missing after processing.")


        print(f"Successfully loaded and standardized {len(event_df)} events.")
        return event_df

    except FileNotFoundError: # This applies if csv_file_obj was a path string
        print(f"Error: The file was not found.") # Removed {csv_file_obj} as it might be StringIO
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading CSV: {e}")
        traceback.print_exc()
        return None