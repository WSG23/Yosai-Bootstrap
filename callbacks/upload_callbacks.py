import base64
import io
import pandas as pd
import json
import traceback
from dash import Input, Output, State, html, dcc
from styles import upload_style_initial, upload_style_success, upload_style_fail
from constants import REQUIRED_INTERNAL_COLUMNS  # ✅ if it's in column_names.py


def register_upload_callbacks(app, icon_upload_default, icon_upload_success, icon_upload_fail):
    @app.callback(
        [
            Output('uploaded-file-store', 'data'),
            Output('csv-headers-store', 'data'),
            Output('dropdown-mapping-area', 'children'),
            Output('confirm-header-map-button', 'style'),
            Output('interactive-setup-container', 'style'),
            Output('processing-status', 'children'),
            Output('upload-icon', 'src'),
            Output('upload-data', 'style'),
            Output('entrance-verification-ui-section', 'style'),
            Output('door-classification-table-container', 'style', allow_duplicate=True),
            Output('graph-output-container', 'style'),
            Output('stats-panels-container', 'style'),
            Output('yosai-custom-header', 'style', allow_duplicate=True),
            Output('onion-graph', 'elements')
        ],
        [Input('upload-data', 'contents')],
        [State('upload-data', 'filename'), State('column-mapping-store', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def handle_upload_and_show_header_mapping(contents, filename, saved_col_mappings_json):
        current_upload_icon_src = icon_upload_default
        current_upload_box_style = upload_style_initial
        yosai_header_style_to_set = {'display': 'none'}
        hide_style = {'display': 'none'}
        show_interactive_setup_style = {
            'display': 'block',
            'padding': '15px',
            'backgroundColor': '#e9e9e9',
            'borderRadius': '5px',
            'margin': '20px auto',
            'width': '95%'
        }
        confirm_button_style_hidden = {
            'display': 'none',
            'marginTop': '15px',
            'backgroundColor': '#007bff',
            'color': 'white',
            'padding': '8px 12px',
            'border': 'none',
            'borderRadius': '4px'
        }
        confirm_button_style_visible = {
            'display': 'block',
            'marginLeft': 'auto',
            'marginRight': 'auto',
            'marginTop': '15px',
            'backgroundColor': '#007bff',
            'color': 'white',
            'padding': '8px 12px',
            'border': 'none',
            'borderRadius': '4px'
        }
        processing_status_msg = ""

        if contents is None:
            return (
                None, None, [],
                confirm_button_style_hidden, hide_style, processing_status_msg,
                current_upload_icon_src, current_upload_box_style,
                hide_style, hide_style, hide_style, hide_style, yosai_header_style_to_set, []
            )

        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            if not filename.lower().endswith('.csv'):
                raise ValueError("Uploaded file is not a CSV.")

            df_preview = pd.read_csv(io.StringIO(decoded.decode('utf-8')), nrows=1)
            headers = df_preview.columns.tolist()
            if not headers:
                raise ValueError("CSV has no headers.")

            saved_col_mappings = json.loads(saved_col_mappings_json) if saved_col_mappings_json else {}
            header_key = json.dumps(sorted(headers))
            loaded_col_map_prefs = saved_col_mappings.get(header_key, {})

            mapping_dropdowns_children = []
            for internal_name, display_text in REQUIRED_INTERNAL_COLUMNS.items():
                pre_sel = None
                if loaded_col_map_prefs:
                    for csv_h, internal_h in loaded_col_map_prefs.items():
                        if internal_h == internal_name and csv_h in headers:
                            pre_sel = csv_h
                            break

                dropdown = dcc.Dropdown(
                    id={'type': 'mapping-dropdown', 'index': internal_name},
                    options=[{'label': h, 'value': h} for h in headers],
                    value=pre_sel,
                    placeholder="Select...",
                    style={
                        'width': '250px',
                        'display': 'inline-block',
                        'marginBottom': '10px',
                        'verticalAlign': 'middle'
                    }
                )

                mapping_dropdowns_children.append(
                    html.Div([
                        html.Label(f"{display_text}:", style={
                            'marginRight': '10px',
                            'width': '200px',
                            'display': 'inline-block',
                            'textAlign': 'right'
                        }),
                        dropdown
                    ])
                )

            processing_status_msg = f"Step 1: Confirm Header Mapping for '{filename}'."
            return (
                contents,
                headers,
                mapping_dropdowns_children,
                confirm_button_style_visible,
                show_interactive_setup_style,
                processing_status_msg,
                icon_upload_success,
                upload_style_success,
                hide_style, hide_style, hide_style, hide_style,
                yosai_header_style_to_set,
                []
            )

        except Exception as e:
            print(f"Error in handle_upload: {e}")
            traceback.print_exc()
            processing_status_msg = f"Error processing '{filename}': {e}"
            return (
                None, None,
                [html.P(processing_status_msg, style={'color': 'red'})],
                confirm_button_style_hidden,
                show_interactive_setup_style,
                processing_status_msg,
                icon_upload_fail,
                upload_style_fail,
                hide_style, hide_style, hide_style, hide_style,
                yosai_header_style_to_set,
                []
            )
