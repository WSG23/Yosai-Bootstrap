# data_io/file_utils.py

import base64
import io

def decode_uploaded_csv(contents_b64: str) -> io.StringIO:
    try:
        _, content_string = contents_b64.split(',')
        decoded = base64.b64decode(content_string).decode('utf-8')
        return io.StringIO(decoded)
    except Exception as e:
        raise ValueError(f"Error decoding uploaded file: {e}")
