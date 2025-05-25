import dash
from dash import Input, Output, State, html, dcc
from dash.dependencies import ALL
import json
import pandas as pd
import traceback
import sys, os
import dash_bootstrap_components as dbc # ✅ NEW IMPORT: For using Bootstrap components

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

# Define Security Levels for the slider here (MUST BE CONSISTENT with core_layout.py)
SECURITY_LEVELS_SLIDER_MAP = {
    0: {"label": "⬜️ Unclassified", "color": "#CCCCCC", "value": "unclassified"},
    1: {"label": "🟢 Green (Public)", "color": "#27AE60", "value": "green"},
    2: {"label": "🟠 Orange (Semi-Restricted)", "color": "#F39C12", "value": "yellow"},
    3: {"label": "🔴 Red (Restricted)", "color": "#C0392B", "value": "red"},
}
# Also a reverse map for pre-selecting from stored data or converting slider output to string value
REVERSE_SECURITY_MAP = {v['value']: k for k, v in SECURITY_LEVELS_SLIDER_MAP.items()}


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
            # ✅ UPDATED STATE IDs FOR CLASSIFICATION INPUTS
            State({'type': 'floor-select', 'index': ALL}, 'value'),
            State({'type': 'floor-select', 'index': ALL}, 'id'),
            State({'type': 'is-ee-check', 'index': ALL}, 'value'),
            State({'type': 'is-ee-check', 'index': ALL}, 'id'),
            State({'type': 'is-stair-check', 'index': ALL}, 'value'),
            State({'type': 'is-stair-check', 'index': ALL}, 'id'),
            State({'type': 'security-level-slider', 'index': ALL}, 'value'), # ✅ Changed from 'security-level-radio'
            State({'type': 'security-level-slider', 'index': ALL}, 'id'),     # ✅ Changed from 'security-level-radio'
            State('num-floors-input', 'value'), # ✅ Changed from 'num-floors-store'
            State('manual-map-toggle', 'value'),
            State('csv-headers-store', 'data'),
            State('manual-door-classifications-store', 'data')
        ],
        prevent_initial_call=True
    )
    def generate_model_final(n_clicks, file_contents_b64, stored_column_mapping_json, all_door_ids_from_store,
                             floor_values, floor_ids, is_ee_values, is_ee_ids, is_stair_values, is_stair_ids,
                             security_slider_values, security_slider_ids, num_floors_from_input, manual_map_choice, # ✅ Updated input names
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

        # ✅ UPDATED LOGIC TO PROCESS SLIDER VALUES
        if manual_map_choice == 'yes' and all_door_ids_from_store: # Removed floor_ids check here as it can be empty initially
            temp = {}
            # Consolidate values by door_id from respective lists
            # It's safer to build dictionaries from the _ids and _values pairs
            floor_map = {f_id['index']: f_val for f_id, f_val in zip(floor_ids, floor_values)}
            is_ee_map = {ee_id['index']: 'is_ee' in ee_val for ee_id, ee_val in zip(is_ee_ids, is_ee_values)}
            is_stair_map = {st_id['index']: 'is_stair' in st_val for st_id, st_val in zip(is_stair_ids, is_stair_values)}
            
            # Map slider integer value to string value (e.g., 1 -> 'green')
            security_map_slider_to_value = {s_id['index']: SECURITY_LEVELS_SLIDER_MAP.get(s_val, {}).get("value", "unclassified")
                                            for s_id, s_val in zip(security_slider_ids, security_slider_values)}

            for door_id in all_door_ids_from_store: # Iterate through all known doors
                # Use .get with a default to handle cases where a door might not have a classification yet
                floor = floor_map.get(door_id, '1') # Default floor 1
                is_ee = is_ee_map.get(door_id, False)
                is_stair = is_stair_map.get(door_id, False)
                security = security_map_slider_to_value.get(door_id, 'green') # Default green

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

            # ✅ Prepare the mapping for `load_csv_event_log` to target DISPLAY NAMES.
            mapping_for_loader_csv_to_display = {}
            for csv_col_name, internal_key in current_mapping_csv_to_internal.items():
                if internal_key in REQUIRED_INTERNAL_COLUMNS:
                    display_name = REQUIRED_INTERNAL_COLUMNS[internal_key]
                    mapping_for_loader_csv_to_display[csv_col_name] = display_name
                else:
                    mapping_for_loader_csv_to_display[csv_col_name] = internal_key

            print(f"Mapping passed to load_csv_event_log (CSV Header -> Display Name): {mapping_for_loader_csv_to_display}")

            df_final = load_csv_event_log(csv_io_for_loader, mapping_for_loader_csv_to_display)

            if df_final is None:
                raise ValueError(
                    "Failed to load CSV for final processing. The `load_csv_event_log` function returned None. "
                    "This strongly suggests an issue within `load_csv_event_log` itself, "
                    "likely due to it not finding expected display-named columns after applying the mapping. "
                    "Consider inspecting the `load_csv_event_log` function in `data_io/csv_loader.py`."
                )

            # --- Final Validation ---
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
            # ✅ Use num_floors_from_input
            config['num_floors'] = num_floors_from_input or GRAPH_PROCESSING_CONFIG['num_floors']

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
                s_tae = f"{len(df_final):,}" 

                # --- Update stats calculations to use display names ---
                if not enriched_df.empty and TIMESTAMP_COL_DISPLAY in enriched_df.columns:
                    if not pd.api.types.is_datetime64_any_dtype(enriched_df[TIMESTAMP_COL_DISPLAY]):
                        enriched_df[TIMESTAMP_COL_DISPLAY] = pd.to_datetime(enriched_df[TIMESTAMP_COL_DISPLAY], errors='coerce')

                    min_d, max_d = enriched_df[TIMESTAMP_COL_DISPLAY].min(), enriched_df[TIMESTAMP_COL_DISPLAY].max()
                    s_er = f"{min_d.strftime('%d.%m.%Y')} - {max_d.strftime('%d.%m.%Y')}" if pd.notna(min_d) and pd.notna(max_d) else "N/A"
                    s_sr = f"Date range: {s_er}"
                    
                    s_dd = f"Days: {enriched_df[TIMESTAMP_COL_DISPLAY].dt.date.nunique()}"
                    
                    if USERID_COL_DISPLAY in enriched_df.columns:
                        s_ut = f"Tokens: {enriched_df[USERID_COL_DISPLAY].nunique()}"
                    
                    if DOORID_COL_DISPLAY in enriched_df.columns:
                        s_adt = [html.Tr([html.Td(d), html.Td(f"{c:,}", style={'textAlign': 'right'})])
                                 for d, c in enriched_df[DOORID_COL_DISPLAY].value_counts().nlargest(5).items()]

                if device_attrs is not None and DOORID_COL_DISPLAY in device_attrs.columns:
                    s_nd = f"Devices: {device_attrs[DOORID_COL_DISPLAY].nunique()}"

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
            Input('num-floors-input', 'value'),             # Trigger when num floors changes
            Input('top-n-entrances-input', 'value'),        # If 'show more' influences displayed doors
            Input('show-more-entrances-button', 'n_clicks') # Explicit button click for "show more"
        ],
        [
            State('all-doors-from-csv-store', 'data'),      # List of all doors extracted
            State('manual-door-classifications-store', 'data'), # Existing classifications
            State('current-entrance-offset-store', 'data'), # For pagination/show more (currently unused)
            State('ranked-doors-store', 'data')              # If you have pre-ranked doors for suggestions (currently unused)
        ],
        prevent_initial_call=True # Only generate when inputs change
    )
    def generate_door_classification_table_content(
        n_clicks_confirm_map, manual_map_choice, num_floors, top_n_entrances, n_clicks_show_more_button,
        all_doors_from_store_data, existing_saved_classifications, current_offset_unused_yet, ranked_doors_unused_yet
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

        # Define options for dropdowns/radio items
        floor_options = [{'label': str(i), 'value': str(i)} for i in range(1, (num_floors or 1) + 1)]
        
        # Generate dbc.Row for each door
        door_rows = []
        # Add a header row
        door_rows.append(
            dbc.Row([
                dbc.Col(html.B("Door ID"), width=3, className="text-start py-2"),
                dbc.Col(html.B("Floor"), width=2, className="text-center py-2"),
                dbc.Col(html.B("Entry/Exit"), width=2, className="text-center py-2"),
                dbc.Col(html.B("Stairway"), width=2, className="text-center py-2"),
                dbc.Col(html.B("Security"), width=3, className="text-center py-2"),
            ], className="g-0 border-bottom fw-bold bg-light") # g-0 removes gutter
        )


        for idx, door_id in enumerate(doors_to_classify): 
            # Pre-select values based on existing classifications
            current_classification = existing_classifications.get(door_id, {})
            pre_sel_floor = current_classification.get('floor', '1')
            pre_sel_is_ee = current_classification.get('is_ee', False)
            pre_sel_is_stair = current_classification.get('is_stair', False)
            
            # Map stored security string value back to slider integer value
            pre_sel_security_val = current_classification.get('security', 'green') # Default to 'green'
            pre_sel_security_slider_val = REVERSE_SECURITY_MAP.get(pre_sel_security_val, 1) # Default slider value 1 (green)

            door_rows.append(
                dbc.Row([
                    dbc.Col(html.Label(door_id, style={"fontWeight": "600", "textAlign": "left"}), width=3, className="d-flex align-items-center"),
                    
                    # Floor Dropdown
                    dbc.Col(dcc.Dropdown(
                        id={'type': 'floor-select', 'index': door_id},
                        options=floor_options,
                        value=pre_sel_floor,
                        clearable=False,
                        style={"width": "100%"}
                    ), width=2, className="d-flex align-items-center"),

                    # Entry/Exit Checkbox
                    dbc.Col(dcc.Checklist(
                        id={'type': 'is-ee-check', 'index': door_id},
                        options=[{'label': ' Entry/Exit', 'value': 'is_ee'}], # Added label for clarity
                        value=['is_ee'] if pre_sel_is_ee else [],
                        inline=True, # Display label next to checkbox
                        className="form-check-inline" # dbc styling
                    ), width=2, className="d-flex align-items-center justify-content-center"),

                    # Stairway Checkbox
                    dbc.Col(dcc.Checklist(
                        id={'type': 'is-stair-check', 'index': door_id},
                        options=[{'label': ' Stairway', 'value': 'is_stair'}], # Added label for clarity
                        value=['is_stair'] if pre_sel_is_stair else [],
                        inline=True, # Display label next to checkbox
                        className="form-check-inline" # dbc styling
                    ), width=2, className="d-flex align-items-center justify-content-center"),

                    # Security Level Slider
                    dbc.Col(dcc.Slider(
                        id={"type": "security-level-slider", "index": door_id}, # Use new ID type for slider
                        min=0,
                        max=3,
                        step=1,
                        value=pre_sel_security_slider_val,
                        marks={k: {
                            "label": v["label"],
                            "style": {
                                "color": v["color"],
                                "fontWeight": "600",
                                "fontSize": "10px" # Smaller font for slider marks
                            }
                        } for k, v in SECURITY_LEVELS_SLIDER_MAP.items()},
                        tooltip={"placement": "bottom", "always_visible": True},
                        className="mb-0 mt-3" # Adjusted margin for slider
                    ), width=3, className="d-flex align-items-center"),
                ], className="g-0 mb-3 border-bottom pb-3") # g-0 removes gutter between cols
            )
        
        print(f"DEBUG: Generated classification table with {len(door_rows)-1} door rows (excluding header).") 
        # Return the list of dbc.Row components, not an html.Table
        return door_rows