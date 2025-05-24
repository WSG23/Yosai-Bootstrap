import pandas as pd
import io, base64

REQUIRED_INTERNAL_COLUMNS = [
    'Timestamp', 'UserID', 'DoorID', 'EventType'
]


def extract_headers_from_base64(contents):
    """Extract CSV headers from a base64-encoded upload."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), nrows=1)
    return df.columns.tolist()


def load_csv_event_log(file_obj, column_mapping):
    """Load CSV, rename columns per mapping, validate required columns."""
    df = pd.read_csv(file_obj)
    # Rename according to mapping {csv_header: internal_name}
    df.rename(columns=column_mapping, inplace=True)

    # Ensure required columns exist
    missing = [c for c in REQUIRED_INTERNAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Type conversions
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df['UserID'] = df['UserID'].astype(str)
    df['DoorID'] = df['DoorID'].astype(str)

    return df
