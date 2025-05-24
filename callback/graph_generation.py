from dash import Input, Output, State, ALL, html\import dash
import json, io, base64
import pandas as pd
from data_io.csv_loader import load_csv_event_log
from processing.onion_model import run_onion_model_processing
from processing.cytoscape_prep import prepare_cytoscape_elements

def register_callbacks(app):
    @app.callback(
        [Output('onion-graph','elements'), Output('processing-status','children'),
         Output('graph-output-container','style'), Output('stats-panels-container','style'),
         Output('yosai-custom-header','style'), Output('total-access-events-H1','children'),
         Output('event-date-range-P','children'), Output('stats-date-range-P','children'),
         Output('stats-days-with-data-P','children'), Output('stats-num-devices-P','children'),
         Output('stats-unique-tokens-P','children'), Output('most-active-devices-table-body','children'),
         Output('manual-door-classifications-store','data'), Output('column-mapping-store','data')],
        Input('confirm-and-generate-button','n_clicks'),
        [State('uploaded-file-store','data'), State('column-mapping-store','data'),
         State('all-doors-from-csv-store','data'), State({'type':'floor-select','index':ALL},'value'),
         State({'type':'floor-select','index':ALL},'id'), State({'type':'is-ee-check','index':ALL},'value'),
         State({'type':'is-ee-check','index':ALL},'id'), State({'type':'is-stair-check','index':ALL},'value'),
         State({'type':'is-stair-check','index':ALL},'id'), State({'type':'security-level-radio','index':ALL},'value'),
         State({'type':'security-level-radio','index':ALL},'id'), State('num-floors-store','data'),
         State('manual-map-toggle','value'), State('csv-headers-store','data'), State('manual-door-classifications-store','data')],
        prevent_initial_call=True
    )
    def generate_model_final(n_clicks, file_contents_b64, col_map_json, all_door_ids,
                              floor_values, floor_ids, is_ee_values, is_ee_ids,
                              is_stair_values, is_stair_ids, security_values, security_ids,
                              num_floors, manual_map_choice, csv_headers, existing_saved_classifications_json):
        graph_elements, graph_style, stats_style, yosai_style = [], {'display':'none'}, {'display':'none'}, {'display':'none'}
        total_events, event_range, stats_range, days, devices, tokens, active_table = "0", "N/A", "N/A", "0", "0", "0", []
        manual_classifications = json.loads(existing_saved_classifications_json) if existing_saved_classifications_json else {}
        final_col_map = col_map_json
        status_msg = "Processing..."
        if not n_clicks or not file_contents_b64 or not col_map_json:
            return graph_elements, status_msg, graph_style, stats_style, yosai_style, total_events, event_range, stats_range, days, devices, tokens, active_table, dash.no_update, dash.no_update
        # Manual classifications
        user_entrances = []
        current_classifications = {}
        if manual_map_choice == 'yes' and all_door_ids:
            for i, door in enumerate(all_door_ids):
                isee = 'is_ee' in (is_ee_values[i] if i < len(is_ee_values) else [])
                current_classifications[door] = {
                    'floor': floor_values[i] if i < len(floor_values) else None,
                    'is_ee': isee,
                    'is_stair': 'is_stair' in (is_stair_values[i] if i < len(is_stair_values) else []),
                    'security': security_values[i] if i < len(security_values) else 'green'
                }
                if isee:
                    user_entrances.append(door)
            if csv_headers:
                key = json.dumps(sorted(csv_headers))
                manual_classifications[key] = current_classifications
        # Load data
        try:
            mapping_dict = json.loads(col_map_json)
            header_key = json.dumps(sorted(csv_headers)) if csv_headers else None
            current_map = mapping_dict.get(header_key, {})
            content = file_contents_b64.split(',')[1]
            df = load_csv_event_log(io.StringIO(base64.b64decode(content).decode()), current_map)
            enriched_df, device_attrs, path_viz, all_paths = run_onion_model_processing(
                df, {'num_floors': num_floors}, confirmed_official_entrances=user_entrances,
                detailed_door_classifications=current_classifications
            )
            nodes, edges = prepare_cytoscape_elements(device_attrs, path_viz, all_paths)
            graph_elements = nodes + edges
            status_msg = "Graph generated!" if graph_elements else "Processed, but no graph elements to display."
            graph_style = {'display':'block'}
            stats_style = {'display':'flex'}
            yosai_style = {'display':'flex'}
            total_events = f"{len(df):,}"
            if 'Timestamp' in enriched_df.columns and enriched_df['Timestamp'].notna().any():
                min_d = enriched_df['Timestamp'].min(); max_d = enriched_df['Timestamp'].max()
                event_range = f"{min_d.strftime('%d.%m.%Y')} - {max_d.strftime('%d.%m.%Y')}"
                stats_range = f"Date range: {event_range}"
                days = f"Days: {enriched_df['Date'].nunique()}"
            devices = f"Devices: {device_attrs['DoorID'].nunique() if not device_attrs.empty else 0}"
            tokens = f"Tokens: {enriched_df['UserID'].nunique()}"
            active_counts = enriched_df['DoorID'].value_counts().nlargest(5)
            active_table = [html.Tr([html.Td(d), html.Td(c)]) for d,c in active_counts.items()]
        except Exception as e:
            status_msg = f"Error: {e}"
            graph_style, stats_style, yosai_style = {'display':'none'}, {'display':'none'}, {'display':'none'}
        return (graph_elements, status_msg, graph_style, stats_style, yosai_style,
                total_events, event_range, stats_range, days, devices, tokens, active_table,
                json.dumps(manual_classifications), final_col_map)

    @app.callback(
        Output('onion-graph','stylesheet'),
        Input('onion-graph','tapNodeData'),
        State('onion-graph','elements'), State('onion-graph','stylesheet'),
        prevent_initial_call=True
    )
    def handle_node_tap_interaction_final(tap_data, current_elements, current_stylesheet):
        base_stylesheet = current_stylesheet or []
        if not tap_data or tap_data.get('is_layer_parent'): return base_stylesheet
        selected_id = tap_data['id']
        dynamic = list(base_stylesheet)
        # Highlight selected node
        dynamic.append({'selector': f'node[id="{selected_id}"]', 'style': {'border-width':'3px','border-color':'#FFDC00'}})
        return dynamic

    @app.callback(
        Output('tap-node-data-output','children'),
        Input('onion-graph','tapNodeData')
    )
    def display_tap_node_data_final(data):
        if data and not data.get('is_layer_parent'):
            details = [f"Tapped: {data.get('label', data.get('id'))}"]
            for key in ['layer','floor','is_entrance','is_stair','security_level']:
                if data.get(key) is not None:
                    details.append(f"{key}: {data.get(key)}")
            return " | ".join(details)
        return "Upload, map headers, classify doors, then click Generate and tap nodes."