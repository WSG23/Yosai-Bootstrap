from dash import Input, Output, State, html, dcc
import json
from data_io.csv_loader import extract_headers_from_base64

def register_callbacks(app):
    @app.callback(
        [Output('upload-status-text', 'children'), Output('mapping-ui-container', 'style'), Output('mapping-ui-container', 'children')],
        Input('upload-data', 'contents'), State('upload-data', 'filename')
    )
    def handle_upload(contents, filename):
        if not contents:
            return "Please upload a CSV file.", {'display':'none'}, []
        try:
            headers = extract_headers_from_base64(contents)
            dropdowns = [html.Div([html.Label(f), dcc.Dropdown(options=[{'label':h,'value':h} for h in headers], placeholder='Select...')])
                         for f in ['Timestamp (Event Time)','UserID','DoorID','EventType']]
            return f"File '{filename}' uploaded.", {'display':'block','marginTop':'20px'}, dropdowns
        except Exception as e:
            return f"Error: {e}", {'display':'none'}, []
