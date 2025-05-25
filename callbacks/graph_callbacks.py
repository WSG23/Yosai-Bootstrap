import dash
from dash import Input, Output, State, html
from dash.dependencies import ALL
import json
import pandas as pd
import traceback

from graph_config import GRAPH_PROCESSING_CONFIG
from styles import actual_default_stylesheet_for_graph

from data_io.csv_loader import load_csv_event_log
from data_io.file_utils import decode_uploaded_csv  # 🔹 NEW
from processing.onion_model import run_onion_model_processing
from processing.cytoscape_prep import prepare_cytoscape_elements
from graph_config import GRAPH_PROCESSING_CONFIG, UI_STYLES
from style_config import UI_VISIBILITY, UI_COMPONENTS



def register_graph_callbacks(app):
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

        # UI styles
        hide_style = UI_STYLES['hide']
        show_style = UI_STYLES['show_block']
        show_stats_style = UI_STYLES['show_flex_stats']


        current_yosai_style = hide_style
        graph_elements = []
        status_msg = "Processing..."

        # Init stats
        s_tae, s_er, s_sr, s_dd, s_nd, s_ut = "0", "N/A", "N/A", "0", "0", "0"
        s_adt = []

        if not n_clicks or not file_contents_b64 or not stored_column_mapping_json:
            return graph_elements, "Missing data or button not clicked.", hide_style, hide_style, hide_style, s_tae, s_er, s_sr, s_dd, s_nd, s_ut, s_adt, dash.no_update, stored_column_mapping_json

        # Load manual classifications
        all_manual_classifications = json.loads(existing_saved_classifications_json) if existing_saved_classifications_json else {}
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
            # Decode and load CSV
            csv_io = decode_uploaded_csv(file_contents_b64)
            all_column_mappings = json.loads(stored_column_mapping_json)
            key = json.dumps(sorted(csv_headers))
            current_mapping = all_column_mappings.get(key, {})

            if not current_mapping:
                raise ValueError("No column mapping found.")

            df_loaded = load_csv_event_log(csv_io, current_mapping)

            # Merge config
            config = GRAPH_PROCESSING_CONFIG.copy()
            config['num_floors'] = num_floors_from_store or GRAPH_PROCESSING_CONFIG['num_floors']

            enriched_df, device_attrs, path_viz, all_paths = run_onion_model_processing(
                df_loaded.copy(),
                config,
                confirmed_official_entrances=confirmed_entrances,
                detailed_door_classifications=current_door_classifications
            )

            if enriched_df is not None:
                nodes, edges = prepare_cytoscape_elements(device_attrs, path_viz, all_paths)
                graph_elements = nodes + edges
                current_yosai_style = show_style if graph_elements else hide_style
                status_msg = "Graph generated!" if graph_elements else "Processed, but no graph elements to display."
                s_tae = f"{len(df_loaded):,}"

                if not enriched_df.empty and 'Timestamp' in enriched_df.columns:
                    min_d, max_d = enriched_df['Timestamp'].min(), enriched_df['Timestamp'].max()
                    s_er = f"{min_d.strftime('%d.%m.%Y')} - {max_d.strftime('%d.%m.%Y')}" if pd.notna(min_d) and pd.notna(max_d) else "N/A"
                    s_sr = f"Date range: {s_er}"
                    if 'Date' in enriched_df.columns:
                        s_dd = f"Days: {enriched_df['Date'].nunique()}"
                    if 'UserID' in enriched_df.columns:
                        s_ut = f"Tokens: {enriched_df['UserID'].nunique()}"
                    if 'DoorID' in enriched_df.columns:
                        s_adt = [html.Tr([html.Td(d), html.Td(f"{c:,}", style={'textAlign': 'right'})])
                                 for d, c in enriched_df['DoorID'].value_counts().nlargest(5).items()]

                if device_attrs is not None and 'DoorID' in device_attrs.columns:
                    s_nd = f"Devices: {device_attrs['DoorID'].nunique()}"

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
        return actual_default_stylesheet_for_graph  # Placeholder

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
                details.append(f"Security: {data['security_level']}")
            return " | ".join(details)
        return "Upload CSV, map headers, (optionally classify doors), then Confirm & Generate. Tap a node for its details."
