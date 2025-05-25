from dash import Input, Output, State, html, dcc, no_update
from dash.dependencies import ALL
import json

def register_mapping_callbacks(app):
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
        if not n_clicks:
            return no_update

        mapping = {
            dropdown_value: dropdown_id['index']
            for dropdown_value, dropdown_id in zip(values, ids)
            if dropdown_value
        }

        updated_mappings = existing_json or {}
        header_key = json.dumps(sorted(csv_headers))
        updated_mappings[header_key] = mapping

        return (
            {'display': 'none'},                  # Hide mapping UI
            {'display': 'block'},                 # Show entrance classification UI
            updated_mappings,                     # Save updated mappings
            "Step 2: Set Classification Options", # Update status message
            {'display': 'none'}                   # Hide confirm button again
        )
