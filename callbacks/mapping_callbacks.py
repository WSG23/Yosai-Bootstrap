from dash import Input, Output, State, html, dcc, no_update
from dash.dependencies import ALL
import json

def register_mapping_callbacks(app):
    @app.callback(
        [
            Output('mapping-ui-section', 'style'),  
            Output('entrance-verification-ui-section', 'style', allow_duplicate=True), # This targets the new dbc.Container
            Output('column-mapping-store', 'data'),
            Output('processing-status', 'children', allow_duplicate=True),
            Output('confirm-header-map-button', 'style', allow_duplicate=True),
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
        if not n_clicks:
            return no_update

        mapping = {
            dropdown_value: dropdown_id['index']
            for dropdown_value, dropdown_id in zip(values, ids)
            if dropdown_value
        }

        if isinstance(existing_json, str):
            updated_mappings = json.loads(existing_json)
        else:
            updated_mappings = existing_json or {}


        header_key = json.dumps(sorted(csv_headers))
        updated_mappings[header_key] = mapping



        return (
            {'display': 'none'},                  # Hide mapping UI
            {'display': 'block', 'width': '95%', 'margin': '0 auto', 'paddingLeft': '15px', 'boxSizing': 'border-box', 'textAlign': 'center'}, # ✅ Show and center entrance classification UI (dbc.Container)
            updated_mappings,                     # Save updated mappings
            "Step 2: Set Classification Options", # Update status message
            {'display': 'none'}                   # Hide confirm button again
        )

    @app.callback(
        [
            Output('door-classification-table-container', 'style'), # This now targets the new dbc.Card for Step 3
            Output('entrance-suggestion-controls', 'style') # Still controlling this div
        ],
        Input('manual-map-toggle', 'value'),
        prevent_initial_call=False # Allows the callback to run on app load
    )
    def toggle_classification_tools(manual_map_choice):
        # Define the styles for visibility AND centering
        hide_style = {'display': 'none'} # Removed margin/padding from base style
        show_style = {'display': 'block'} # Removed margin/padding from base style

        if manual_map_choice == 'yes':
            return show_style, show_style
        else:
            return hide_style, hide_style