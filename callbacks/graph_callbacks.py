import dash
from dash import Input, Output, State, html, dcc
from dash.dependencies import ALL
import json
import pandas as pd
import traceback
import sys, os

# This is important for module imports. Ensure this path is correct relative to your project root.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..')) # Go up one level from 'callbacks'
sys.path.append(project_root)


from processing.graph_config import GRAPH_PROCESSING_CONFIG, UI_STYLES
from styles.graph_styles import actual_default_stylesheet_for_graph
from data_io.csv_loader import load_csv_event_log # This function is key
from data_io.file_utils import decode_uploaded_csv
from processing.onion_model import run_onion_model_processing
from processing.cytoscape_prep import prepare_cytoscape_elements
from constants.constants import REQUIRED_INTERNAL_COLUMNS 

def fuzzy_match_columns(csv_columns, internal_keys):
    """Best-effort fuzzy match between internal keys and CSV column names."""
    from difflib import get_close_matches
    mapping = {}
    for internal_key, expected_label in internal_keys.items():
        # Prioritize matching display labels directly in CSV for mapping, as load_csv_event_log will expect them.
        if expected_label in csv_columns:
            mapping[expected_label] = internal_key # Map CSV column (display_name) to internal key
        # Fallback to internal key if display label not found
        elif internal_key in csv_columns:
            mapping[internal_key] = internal_key # Map CSV column (internal_key) to internal key
        else:
            # Fuzzy match on expected label
            matches = get_close_matches(expected_label, csv_columns, n=1, cutoff=0.6)
            if matches:
                mapping[matches[0]] = internal_key
            else:
                # Fuzzy match on internal key
                matches2 = get_close_matches(internal_key, csv_columns, n=1, cutoff=0.6)
                if matches2:
                    mapping[matches2[0]] = internal_key
    return mapping

def register_graph_callbacks(app):
    # Define display names for clarity and consistency within this file
    DOORID_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['DoorID']
    USERID_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['UserID']
    EVENTTYPE_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['EventType']
    TIMESTAMP_COL_DISPLAY = REQUIRED_INTERNAL_COLUMNS['Timestamp']


    @app.callback(
        [
            Output('onion-graph', 'elements', allow_duplicate=True),
            Output('processing-status', 'children', allow_duplicate=True),
            Output('graph-output-container', 'style', allow_duplicate=True),
            Output('stats-panels-container', 'style', allow_duplicate=True),
            Output('yosai-custom-header', 'style', allow_duplicate=True),
            Output('total-access-events-H1', 'children'),
            Output('event-date-range-P', 'children'),
            Output('stats-date-range-P', 'children'),
            Output('stats-days-with-data-P', 'children'),
            Output('stats-num-devices-P', 'children'),
            Output('stats-unique-tokens-P', 'children'),
            Output('most-active-devices-table-body', 'children'),
            Output('manual-door-classifications-store', 'data', allow_duplicate=True),
            Output('column-mapping-store', 'data', allow_duplicate=True)
        ],
        Input('confirm-and-generate-button', 'n_clicks'),
        [
            State('uploaded-file-store', 'data'),
            State('column-mapping-store', 'data'),
            State('all-doors-from-csv-store', 'data'),
            State({'type': 'floor-select', 'index': ALL}, 'value'),
            State({'type': 'floor-select', 'index': ALL}, 'id'),
            State({'type': 'is-ee-check', 'index': ALL}, 'value'),
            State({'type': 'is-ee-check', 'index': ALL}, 'id'),
            State({'type': 'is-stair-check', 'index': ALL}, 'value'),
            State({'type': 'is-stair-check', 'index': ALL}, 'id'),
            State({'type': 'security-level-radio', 'index': ALL}, 'value'),
            State({'type': 'security-level-radio', 'index': ALL}, 'id'),
            State('num-floors-store', 'data'),
            State('manual-map-toggle', 'value'),
            State('csv-headers-store', 'data'),
            State('manual-door-classifications-store', 'data')
        ],
        prevent_initial_call=True
    )
    def generate_model_final(n_clicks, file_contents_b64, stored_column_mapping_json, all_door_ids_from_store,
                             floor_values, floor_ids, is_ee_values, is_ee_ids, is_stair_values, is_stair_ids,
                             security_values, security_ids, num_floors_from_store, manual_map_choice,
                             csv_headers, existing_saved_classifications_json):

        hide_style = UI_STYLES['hide']
        show_style = UI_STYLES['show_block']
        show_stats_style = UI_STYLES['show_flex_stats']

        current_yosai_style = hide_style
        graph_elements = []
        status_msg = "Processing..."

        s_tae, s_er, s_sr, s_dd, s_nd, s_ut = "0", "N/A", "N/A", "0", "0", "0"
        s_adt = []

        if not n_clicks or not file_contents_b64:
            return graph_elements, "Missing data or button not clicked.", hide_style, hide_style, hide_style, s_tae, s_er, s_sr, s_dd, s_nd, s_ut, s_adt, dash.no_update, stored_column_mapping_json

        if isinstance(existing_saved_classifications_json, str):
            all_manual_classifications = json.loads(existing_saved_classifications_json)
        else:
            all_manual_classifications = existing_saved_classifications_json or {}

        current_door_classifications = {}
        confirmed_entrances = []

        if manual_map_choice == 'yes' and all_door_ids_from_store and floor_ids:
            temp = {}
            for i in range(len(floor_ids)):
                door_id = floor_ids[i]['index']
                floor = floor_values[i] if floor_values and i < len(floor_values) else '1'
                is_ee = bool(is_ee_values and i < len(is_ee_values) and 'is_ee' in is_ee_values[i])
                is_stair = bool(is_stair_values and i < len(is_stair_values) and 'is_stair' in is_stair_values[i])
                security = security_values[i] if security_values and i < len(security_values) else 'green'

                temp[door_id] = {
                    'floor': str(floor),
                    'is_ee': is_ee,
                    'is_stair': is_stair,
                    'security': security
                }

                if is_ee:
                    confirmed_entrances.append(door_id)

            current_door_classifications = temp
            if csv_headers:
                key = json.dumps(sorted(csv_headers))
                all_manual_classifications[key] = temp
        else:
            status_msg += " Using heuristic for entrances."

        try:
            # Re-decode CSV stream for load_csv_event_log. Each time it's used, a new stream is needed.
            csv_io_for_loader = decode_uploaded_csv(file_contents_b64)
            
            if isinstance(stored_column_mapping_json, str):
                all_column_mappings = json.loads(stored_column_mapping_json)
            else:
                all_column_mappings = stored_column_mapping_json or {}

            header_key = json.dumps(sorted(csv_headers)) if csv_headers else None
            
            # current_mapping_csv_to_internal will be CSV_Header -> internal_key as stored by mapping_callbacks
            current_mapping_csv_to_internal = {} 

            # Attempt to load stored mapping, but ensure it covers all required internal keys
            stored_map = all_column_mappings.get(header_key) if header_key else None
            if isinstance(stored_map, dict) and set(stored_map.values()) >= set(REQUIRED_INTERNAL_COLUMNS.keys()):
                current_mapping_csv_to_internal = stored_map
            else:
                if stored_map:
                    print("🤖 Stored mapping incomplete, falling back to fuzzy matching")
                
                # When fuzzy matching, we need the actual CSV column names to match against
                temp_csv_io_peek = decode_uploaded_csv(file_contents_b64) # Fresh stream for peeking
                df_peek_columns = pd.read_csv(temp_csv_io_peek, nrows=0).columns.tolist()
                current_mapping_csv_to_internal = fuzzy_match_columns(df_peek_columns, REQUIRED_INTERNAL_COLUMNS)
                print("🤖 Fuzzy Mapping Used (CSV Header -> Internal Key):", current_mapping_csv_to_internal)

            if not current_mapping_csv_to_internal:
                raise ValueError("No column mapping found. Please ensure all required columns are mapped in the previous step.")

            # Validate that all REQUIRED_INTERNAL_COLUMNS internal keys are targeted by the mapping
            required_internal_keys_set = set(REQUIRED_INTERNAL_COLUMNS.keys())
            mapped_internal_keys_set = set(current_mapping_csv_to_internal.values())
            if not required_internal_keys_set.issubset(mapped_internal_keys_set):
                missing_internal_keys = required_internal_keys_set - mapped_internal_keys_set
                raise ValueError(f"Missing mapped internal keys: {', '.join(missing_internal_keys)}. Please ensure all essential columns are mapped in the dropdowns.")

            # ✅ CRITICAL CHANGE: Prepare the mapping for `load_csv_event_log` to target DISPLAY NAMES.
            # This is the crucial step. We are now sure `load_csv_event_log` expects display names for its internal checks.
            mapping_for_loader_csv_to_display = {}
            for csv_col_name, internal_key in current_mapping_csv_to_internal.items():
                if internal_key in REQUIRED_INTERNAL_COLUMNS:
                    display_name = REQUIRED_INTERNAL_COLUMNS[internal_key]
                    mapping_for_loader_csv_to_display[csv_col_name] = display_name
                else:
                    # If an internal_key from current_mapping_csv_to_internal isn't in REQUIRED_INTERNAL_COLUMNS,
                    # keep it as the internal_key itself as a fallback, or decide to drop it.
                    mapping_for_loader_csv_to_display[csv_col_name] = internal_key

            print(f"Mapping passed to load_csv_event_log (CSV Header -> Display Name): {mapping_for_loader_csv_to_display}")

            # ✅ Now, load_csv_event_log should return a DataFrame with display-named columns.
            df_final = load_csv_event_log(csv_io_for_loader, mapping_for_loader_csv_to_display)

            if df_final is None:
                # This error now specifically points to an issue within load_csv_event_log
                # given it's supposed to return display-named columns.
                raise ValueError(
                    "Failed to load CSV for final processing. The `load_csv_event_log` function returned None. "
                    "This strongly suggests an issue within `load_csv_event_log` itself, "
                    "likely due to it not finding expected display-named columns after applying the mapping. "
                    "Consider inspecting the `load_csv_event_log` function in `data_io/csv_loader.py`."
                )

            # --- Final Validation (already present, but good to keep) ---
            missing_display_columns_in_final_df = [
                display_name for internal_key, display_name in REQUIRED_INTERNAL_COLUMNS.items()
                if display_name not in df_final.columns
            ]

            if missing_display_columns_in_final_df:
                raise ValueError(
                    f"Final DataFrame is missing critical display columns AFTER `load_csv_event_log` processing: "
                    f"{', '.join(missing_display_columns_in_final_df)}. "
                    f"Current DataFrame columns: {df_final.columns.tolist()}. "
                    f"This indicates that `load_csv_event_log` did not correctly rename columns to display names."
                )

            # --- Data Processing and Model Generation (using df_final) ---
            config = GRAPH_PROCESSING_CONFIG.copy()
            config['num_floors'] = num_floors_from_store or GRAPH_PROCESSING_CONFIG['num_floors']

            enriched_df, device_attrs, path_viz, all_paths = run_onion_model_processing(
                df_final.copy(), # Pass df_final (with display names) to run_onion_model_processing
                config,
                confirmed_official_entrances=confirmed_entrances,
                detailed_door_classifications=current_door_classifications
            )

            if enriched_df is not None:
                nodes, edges = prepare_cytoscape_elements(device_attrs, path_viz, all_paths)
                graph_elements = nodes + edges
                current_yosai_style = show_style if graph_elements else hide_style
                status_msg = "Graph generated!" if graph_elements else "Processed, but no graph elements to display."
                s_tae = f"{len(df_final):,}" # Use df_final for total events if enriched_df is a subset

                # --- Update stats calculations to use display names ---
                if not enriched_df.empty and 'Timestamp (Event Time)' in enriched_df.columns:
                    # Ensure the timestamp column is datetime type for operations
                    if not pd.api.types.is_datetime64_any_dtype(enriched_df['Timestamp (Event Time)']):
                        enriched_df['Timestamp (Event Time)'] = pd.to_datetime(enriched_df['Timestamp (Event Time)'], errors='coerce')

                    min_d, max_d = enriched_df['Timestamp (Event Time)'].min(), enriched_df['Timestamp (Event Time)'].max()
                    s_er = f"{min_d.strftime('%d.%m.%Y')} - {max_d.strftime('%d.%m.%Y')}" if pd.notna(min_d) and pd.notna(max_d) else "N/A"
                    s_sr = f"Date range: {s_er}"
                    
                    # Calculate unique days from the timestamp column directly
                    s_dd = f"Days: {enriched_df['Timestamp (Event Time)'].dt.date.nunique()}"
                    
                    if 'UserID (Person Identifier)' in enriched_df.columns:
                        s_ut = f"Tokens: {enriched_df['UserID (Person Identifier)'].nunique()}"
                    
                    if 'DoorID (Device Name)' in enriched_df.columns:
                        s_adt = [html.Tr([html.Td(d), html.Td(f"{c:,}", style={'textAlign': 'right'})])
                                 for d, c in enriched_df['DoorID (Device Name)'].value_counts().nlargest(5).items()]

                if device_attrs is not None and 'DoorID (Device Name)' in device_attrs.columns:
                    s_nd = f"Devices: {device_attrs['DoorID (Device Name)'].nunique()}"

                if not s_adt:
                    s_adt = [html.Tr([html.Td("N/A", colSpan=2)])]

            else:
                status_msg = "Error in processing: incomplete result."

            return (
                graph_elements, status_msg,
                show_style if graph_elements else hide_style,
                show_stats_style if graph_elements else hide_style,
                current_yosai_style,
                s_tae, s_er, s_sr, s_dd, s_nd, s_ut, s_adt,
                json.dumps(all_manual_classifications) if all_manual_classifications else dash.no_update,
                stored_column_mapping_json
            )

        except Exception as e:
            traceback.print_exc()
            return (
                [], f"Error: {str(e)}",
                hide_style, hide_style, hide_style,
                s_tae, s_er, s_sr, s_dd, s_nd, s_ut, s_adt,
                dash.no_update, stored_column_mapping_json
            )

    @app.callback(
        Output('onion-graph', 'stylesheet', allow_duplicate=True),
        Input('onion-graph', 'tapNodeData'),
        [State('onion-graph', 'elements'), State('onion-graph', 'stylesheet')],
        prevent_initial_call=True
    )
    def handle_node_tap_interaction_final(tap_data, current_elements, current_stylesheet):
        return actual_default_stylesheet_for_graph

    @app.callback(
        Output('tap-node-data-output', 'children'),
        Input('onion-graph', 'tapNodeData')
    )
    def display_tap_node_data_final(data):
        if data and not data.get('is_layer_parent'):
            details = [f"Tapped: {data.get('label', data.get('id'))}"]
            if 'layer' in data:
                details.append(f"Layer: {data['layer']}")
            if 'floor' in data:
                details.append(f"Floor: {data['floor']}")
            if data.get('is_entrance'):
                details.append("Type: Entrance/Exit")
            if data.get('is_stair'):
                details.append("Type: Staircase")
            if 'security_level' in data:
                details.append(f"Security: {data['security_level']}" )
            return " | ".join(details)
        return "Upload CSV, map headers, (optionally classify doors), then Confirm & Generate. Tap a node for its details."

    # --- NEW CALLBACK TO GENERATE DOOR CLASSIFICATION TABLE CONTENT ---
    @app.callback(
        Output('door-classification-table', 'children'), # This is the target div
        [
            Input('confirm-header-map-button', 'n_clicks'), # Trigger when mapping confirmed
            Input('manual-map-toggle', 'value'),            # Trigger when user selects Yes/No for manual map
            Input('num-floors-input', 'value'),             # If changing floors affects options
            Input('top-n-entrances-input', 'value'),        # If 'show more' influences displayed doors
            Input('show-more-entrances-button', 'n_clicks') # Explicit button click for "show more"
        ],
        [
            State('all-doors-from-csv-store', 'data'),      # List of all doors extracted
            State('manual-door-classifications-store', 'data'), # Existing classifications
            State('current-entrance-offset-store', 'data'), # For pagination/show more
            State('ranked-doors-store', 'data')              # If you have pre-ranked doors for suggestions
        ],
        prevent_initial_call=True # Only generate when inputs change
    )
    def generate_door_classification_table_content(
        n_clicks_confirm_map, manual_map_choice, num_floors, top_n_entrances, n_clicks_show_more_button,
        all_doors_from_store_data, existing_saved_classifications, current_offset_unused_yet, ranked_doors_unused_yet # Unused states can be removed if not needed for first pass
    ):
        # Only generate if manual mapping is chosen and there are doors
        if manual_map_choice != 'yes' or not all_doors_from_store_data:
            print("DEBUG: Not in manual mode or no doors available for classification table.")
            return [] # Return empty list if not in manual mode or no doors

        doors_to_classify = sorted(all_doors_from_store_data) # Use the pre-stored list of all doors

        # Load existing classifications if any
        if isinstance(existing_saved_classifications, str):
            existing_classifications = json.loads(existing_saved_classifications)
        else:
            existing_classifications = existing_saved_classifications or {}

        # Define options for dropdowns/radio items (these should align with your model's expectations)
        floor_options = [{'label': str(i), 'value': str(i)} for i in range(1, (num_floors or 1) + 1)]
        security_options = [
            {'label': 'Green (Public)', 'value': 'green'},
            {'label': 'Yellow (Semi-Restricted)', 'value': 'yellow'},
            {'label': 'Red (Restricted)', 'value': 'red'}
        ]
        
        # Add a header row for the table
        table_header = html.Thead(html.Tr([
            html.Th("Door ID", style={'textAlign': 'left', 'padding': '8px'}),
            html.Th("Floor", style={'padding': '8px'}),
            html.Th("Entry/Exit", style={'padding': '8px'}),
            html.Th("Stairway", style={'padding': '8px'}),
            html.Th("Security Level", style={'padding': '8px'})
        ], style={'backgroundColor': '#f2f2f2', 'borderBottom': '2px solid #ddd'}))

        table_rows = []
        for door_id in doors_to_classify: # Iterate through the sorted unique door IDs
            # Pre-select values based on existing classifications
            current_classification = existing_classifications.get(door_id, {})
            pre_sel_floor = current_classification.get('floor', '1')
            pre_sel_is_ee = current_classification.get('is_ee', False)
            pre_sel_is_stair = current_classification.get('is_stair', False)
            pre_sel_security = current_classification.get('security', 'green')

            table_rows.append(
                html.Tr([
                    html.Td(door_id, style={'fontWeight': 'bold', 'padding': '8px'}),
                    html.Td(dcc.Dropdown(
                        id={'type': 'floor-select', 'index': door_id},
                        options=floor_options,
                        value=pre_sel_floor,
                        clearable=False,
                        style={'width': '100px'}
                    ), style={'padding': '8px'}),
                    html.Td(dcc.Checklist(
                        id={'type': 'is-ee-check', 'index': door_id},
                        options=[{'label': '', 'value': 'is_ee'}],
                        value=['is_ee'] if pre_sel_is_ee else [],
                        style={'textAlign': 'center', 'padding': '8px'}
                    )),
                    html.Td(dcc.Checklist(
                        id={'type': 'is-stair-check', 'index': door_id},
                        options=[{'label': '', 'value': 'is_stair'}],
                        value=['is_stair'] if pre_sel_is_stair else [],
                        style={'textAlign': 'center', 'padding': '8px'}
                    )),
                    html.Td(dcc.RadioItems(
                        id={'type': 'security-level-radio', 'index': door_id},
                        options=security_options,
                        value=pre_sel_security,
                        inline=True,
                        labelStyle={'display': 'inline-block', 'marginRight': '5px'},
                        style={'width': '200px', 'padding': '8px'}
                    ))
                ], style={'borderBottom': '1px solid #eee'} if door_id != doors_to_classify[-1] else {}) # Add border except last row
            )
        
        print(f"DEBUG: Generated classification table with {len(table_rows)-1} door rows.") # -1 for header
        return html.Table([table_header, html.Tbody(table_rows)], 
                           style={'width': '100%', 'borderCollapse': 'collapse', 'border': '1px solid #ddd'})