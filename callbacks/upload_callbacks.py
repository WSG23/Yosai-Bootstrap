import base64
import io
import pandas as pd
import json
import traceback
from dash import Input, Output, State, html, dcc
from styles.graph_styles import upload_style_initial, upload_style_success, upload_style_fail, upload_icon_img_style
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
            Output('onion-graph', 'elements'),
            Output('all-doors-from-csv-store', 'data'), # ✅ ADDED THIS OUTPUT
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
                hide_style, hide_style, hide_style, hide_style, yosai_header_style_to_set, [],
                None # ✅ ADDED THIS FOR all-doors-from-csv-store
            )

        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            if not filename.lower().endswith('.csv'):
                raise ValueError("Uploaded file is not a CSV.")

            # Load the full DataFrame here to get all unique Door IDs
            df_full_for_doors = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            headers = df_full_for_doors.columns.tolist() # Use full df to get all headers
            if not headers:
                raise ValueError("CSV has no headers.")

            # Apply a preliminary mapping to get the DoorID column by its display name
            # This logic assumes the structure of column_mapping_store is consistent
            # with how you define dropdowns (CSV_Header -> internal_key)
            if isinstance(saved_col_mappings_json, str):
                saved_col_mappings = json.loads(saved_col_mappings_json)
            else:
                saved_col_mappings = saved_col_mappings_json or {}

            header_key = json.dumps(sorted(headers))
            loaded_col_map_prefs = saved_col_mappings.get(header_key, {}) # This maps CSV header -> internal_key

            # Create a map from CSV Header to Display Name for this temporary DF for doors
            temp_mapping_for_doors = {}
            for csv_h_selected, internal_k in loaded_col_map_prefs.items():
                if internal_k in REQUIRED_INTERNAL_COLUMNS:
                    temp_mapping_for_doors[csv_h_selected] = REQUIRED_INTERNAL_COLUMNS[internal_k]
                else:
                    # If an internal_key from loaded_col_map_prefs isn't in REQUIRED_INTERNAL_COLUMNS,
                    # keep it as the internal_key itself as a fallback, or decide to drop it.
                    temp_mapping_for_doors[csv_h_selected] = internal_k

            # Apply this temporary mapping to df_full_for_doors
            df_full_for_doors.rename(columns=temp_mapping_for_doors, inplace=True)

            DOORID_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['DoorID'] # Get display name

            all_unique_doors = []
            if DOORID_COL_DISPLAY in df_full_for_doors.columns:
                all_unique_doors = sorted(df_full_for_doors[DOORID_COL_DISPLAY].astype(str).unique().tolist())
                print(f"DEBUG: Extracted {len(all_unique_doors)} unique doors for classification.")
            else:
                print(f"Warning: '{DOORID_COL_DISPLAY}' column not found after preliminary mapping for door list extraction.")


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
                [], # Empty onion-graph elements initially
                all_unique_doors # ✅ ADDED THIS FOR all-doors-from-csv-store
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
                [], # Empty onion-graph elements
                None # ✅ ADDED THIS FOR all-doors-from-csv-store on error
            )