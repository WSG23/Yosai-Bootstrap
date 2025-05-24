from dash import Input, Output, State, html, dcc, no_update
from data_io.csv_loader import extract_headers_from_base64

# Internal fields to map: internal key -> display label
INTERNAL_FIELDS = {
    'Timestamp': 'Timestamp (Event Time)',
    'UserID': 'UserID (Person Identifier)',
    'DoorID': 'DoorID (Device Name)',
    'EventType': 'EventType (Access Result)'
}

def register_callbacks(app):
    @app.callback(
        [
            Output('upload-status-text', 'children'),
            Output('mapping-ui-container', 'style'),
            Output('mapping-ui-container', 'children')
        ],
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        prevent_initial_call=True
    )
    def handle_upload(contents, filename):
        """
        Handle CSV upload: validate file, extract headers, and display mapping dropdowns.
        """
        hide = {'display': 'none'}
        show = {'display': 'block', 'marginTop': '20px'}

        if not contents:
            # No file uploaded yet
            return "Please upload a CSV file.", hide, []

        try:
            # Decode and preview headers
            headers = extract_headers_from_base64(contents)
            # Build mapping UI with one dropdown per required field
            dropdowns = []
            for key, label in INTERNAL_FIELDS.items():
                dropdowns.append(
                    html.Div([
                        html.Label(f"{label}:", style={'marginRight': '8px'}),
                        dcc.Dropdown(
                            id={'type': 'mapping-dropdown', 'index': key},
                            options=[{'label': h, 'value': h} for h in headers],
                            placeholder='Select header',
                            style={'width': '200px', 'display': 'inline-block'}
                        )
                    ], style={'marginBottom': '10px'})
                )
            status_msg = f"File '{filename}' uploaded. Please map CSV headers."
            return status_msg, show, dropdowns

        except Exception as err:
            # On error, hide mapping UI and show error message
            return f"Error processing '{filename}': {err}", hide, []
# File: callbacks/mapping_flow.py
from dash import Input, Output, State, ALL, html, dcc
import json, io, base64
import dash
from data_io.csv_loader import load_csv_event_log

def register_callbacks(app):
    @app.callback(
        [
            Output('mapping-ui-container', 'style'),
            Output('entrance-verification-ui-section', 'style'),
            Output('column-mapping-store', 'data'),
            Output('processing-status', 'children'),
            Output('confirm-header-map-button', 'style')
        ],
        Input('confirm-header-map-button', 'n_clicks'),
        [
            State({'type': 'mapping-dropdown', 'index': ALL}, 'value'),
            State({'type': 'mapping-dropdown', 'index': ALL}, 'id'),
            State('csv-headers-store', 'data'),
            State('column-mapping-store', 'data')
        ],
        prevent_initial_call=True
    )
    def show_manual_classification_options(n_clicks, values, ids, csv_headers, existing_json):
        """
        After header mapping, store mappings and reveal the manual classification section.
        """
        if not n_clicks:
            return dash.no_update
        # Build and validate mapping
        mapping = {}
        for val, id_dict in zip(values, ids):
            if val:
                mapping[val] = id_dict['index']
            else:
                return (dash.no_update, dash.no_update,
                        dash.no_update, "Error: Complete all required header mappings.",
                        dash.no_update)
        # Persist mapping under sorted header key
        all_maps = json.loads(existing_json or "{}")
        key = json.dumps(sorted(csv_headers or []))
        all_maps[key] = mapping
        serialized = json.dumps(all_maps)
        return (
            {'display': 'none'},
            {'display': 'block'},
            serialized,
            "Step 2: Setup facility details and classify doors.",
            {'display': 'none'}
        )

    @app.callback(
        Output('num-floors-input-container', 'style'),
        Input('manual-map-toggle', 'value')
    )
    def toggle_num_floors(manual_choice):
        """
        Show floor input only when manual classification is enabled.
        """
        return {'display': 'block'} if manual_choice == 'yes' else {'display': 'none'}

    @app.callback(
        [
            Output('door-classification-table-container', 'style'),
            Output('door-classification-table', 'children'),
            Output('all-doors-from-csv-store', 'data'),
            Output('num-floors-store', 'data'),
            Output('entrance-suggestion-controls', 'style')
        ],
        Input('num-floors-input', 'value'),
        [
            State('manual-map-toggle', 'value'),
            State('uploaded-file-store', 'data'),
            State('column-mapping-store', 'data'),
            State('manual-door-classifications-store', 'data'),
            State('csv-headers-store', 'data')
        ],
        prevent_initial_call=True
    )
    def populate_door_classification(num_floors, manual_choice, file_data, col_map_json, saved_class_json, csv_headers):
        """
        Populate door classification UI table when manual classification is chosen.
        """
        if manual_choice != 'yes' or not file_data or not col_map_json:
            return {'display': 'none'}, [], None, dash.no_update, {'display': 'none'}
        # Decode and parse CSV
        _, b64 = file_data.split(',', 1)
        decoded = base64.b64decode(b64).decode('utf-8')
        mapping_dict = json.loads(col_map_json)
        key = json.dumps(sorted(csv_headers or []))
        column_mapping = mapping_dict.get(key, {})
        df = load_csv_event_log(io.StringIO(decoded), column_mapping)
        # Build table rows
        doors = sorted(df['DoorID'].astype(str).unique())
        # Dropdown and checklist options
        floor_opts = [{'label': str(i), 'value': i} for i in range(1, num_floors + 1)]
        security_opts = [
            {'label': 'Low', 'value': 'green'},
            {'label': 'MedLow', 'value': 'yellow'},
            {'label': 'MedHigh', 'value': 'orange'},
            {'label': 'Crit', 'value': 'red'}
        ]
        rows = []
        for door in doors:
            rows.append(html.Tr([
                html.Td(door),
                html.Td(dcc.Dropdown(id={'type': 'floor-select', 'index': door}, options=floor_opts, clearable=False)),
                html.Td(dcc.Checklist(id={'type': 'is-ee-check', 'index': door}, options=[{'label': '', 'value': 'is_ee'}], inline=True)),
                html.Td(dcc.Checklist(id={'type': 'is-stair-check', 'index': door}, options=[{'label': '', 'value': 'is_stair'}], inline=True)),
                html.Td(dcc.RadioItems(id={'type': 'security-level-radio', 'index': door}, options=security_opts, inline=True))
            ]))
        table = html.Table([
            html.Thead(html.Tr([
                html.Th("Device Name", style={'minWidth': '180px'}),
                html.Th("Floor #"), html.Th("E/E?"), html.Th("Stair?"), html.Th("Security Lvl")
            ])),
            html.Tbody(rows)
        ], style={'width': '100%', 'fontSize': '0.9em'})
        return (
            {'display': 'block', 'marginTop': '15px'},
            table,
            doors,
            num_floors,
            {'display': 'block'}
        )