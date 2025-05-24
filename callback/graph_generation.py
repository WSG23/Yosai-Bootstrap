# File: callbacks/graph_generation.py
from dash import Input, Output, State, ALL, html, no_update
import dash
import json, io, base64, traceback
import pandas as pd
from data_io.csv_loader import load_csv_event_log
from processing.onion_model import run_onion_model_processing
from processing.cytoscape_prep import prepare_cytoscape_elements


def register_callbacks(app):
    @app.callback(
        [
            Output('processing-status','children'),
            Output('onion-graph','elements'),
            Output('graph-output-container','style'),
            Output('stats-panels-container','style'),
            Output('yosai-custom-header','style'),
            Output('total-access-events-H1','children'),
            Output('event-date-range-P','children'),
            Output('stats-date-range-P','children'),
            Output('stats-days-with-data-P','children'),
            Output('stats-num-devices-P','children'),
            Output('stats-unique-tokens-P','children'),
            Output('most-active-devices-table-body','children'),
            Output('manual-door-classifications-store','data'),
            Output('column-mapping-store','data')
        ],
        Input('confirm-and-generate-button','n_clicks'),
        [
            State('uploaded-file-store','data'),
            State('column-mapping-store','data'),
            State('all-doors-from-csv-store','data'),
            State({'type':'floor-select','index':ALL},'value'),
            State({'type':'floor-select','index':ALL},'id'),
            State({'type':'is-ee-check','index':ALL},'value'),
            State({'type':'is-ee-check','index':ALL},'id'),
            State({'type':'is-stair-check','index':ALL},'value'),
            State({'type':'is-stair-check','index':ALL},'id'),
            State({'type':'security-level-radio','index':ALL},'value'),
            State({'type':'security-level-radio','index':ALL},'id'),
            State('num-floors-store','data'),
            State('manual-map-toggle','value'),
            State('csv-headers-store','data'),
            State('manual-door-classifications-store','data')
        ],
        prevent_initial_call=True
    )
    def generate_graph(
        n_clicks,
        file_contents_b64,
        col_map_json,
        all_doors,
        floor_values, floor_ids,
        ee_values, ee_ids,
        stair_values, stair_ids,
        security_values, security_ids,
        num_floors,
        manual_choice,
        csv_headers,
        saved_classifications_json
    ):
        # Initial in-flight status
        status = "Processing..."
        # Pre-default UI values
        if not (n_clicks and file_contents_b64 and col_map_json):
            return status, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        # Load existing manual classifications
        manual_classifications = json.loads(saved_classifications_json or "{}")
        details_map = {}
        selected_entrances = []

        # Gather manual door classifications if enabled
        if manual_choice == 'yes' and all_doors:
            for i, door in enumerate(all_doors):
                is_ee = 'is_ee' in (ee_values[i] if i < len(ee_values) else [])
                details_map[door] = {
                    'floor': floor_values[i] if i < len(floor_values) else None,
                    'is_ee': is_ee,
                    'is_stair': 'is_stair' in (stair_values[i] if i < len(stair_values) else []),
                    'security': security_values[i] if i < len(security_values) else 'green'
                }
                if is_ee:
                    selected_entrances.append(door)
            header_key = csv_headers and json.dumps(sorted(csv_headers)) or ""
            manual_classifications[header_key] = details_map

        try:
            # Decode and load CSV with mapping
            mapping_dict = json.loads(col_map_json)
            header_key = json.dumps(sorted(csv_headers or []))
            current_map = mapping_dict.get(header_key, {})
            raw = base64.b64decode(file_contents_b64.split(',')[1]).decode('utf-8')
            df = load_csv_event_log(io.StringIO(raw), current_map)

            # Run onion model processing
            enriched_df, device_attrs, path_viz, all_paths = run_onion_model_processing(
                df,
                {'num_floors': num_floors},
                confirmed_official_entrances=selected_entrances,
                detailed_door_classifications=details_map
            )

            # Prepare Cytoscape elements
            nodes, edges = prepare_cytoscape_elements(device_attrs, path_viz, all_paths)
            elements = nodes + edges

            # Build stats
            total = f"{len(df):,}"
            if not enriched_df.empty and enriched_df['Timestamp'].notna().any():
                start, end = enriched_df['Timestamp'].min(), enriched_df['Timestamp'].max()
                date_range = f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}"
                stats_date = f"Date range: {date_range}"
                days = f"Days: {enriched_df['Date'].nunique()}"
            else:
                date_range = stats_date = "N/A"
                days = "0"
            devices = f"Devices: {device_attrs['DoorID'].nunique() if not device_attrs.empty else 0}"
            tokens = f"Tokens: {enriched_df['UserID'].nunique() if 'UserID' in enriched_df else 0}"
            active_rows = [html.Tr([html.Td(d), html.Td(c)]) for d, c in enriched_df['DoorID'].value_counts().nlargest(5).items()]

            # Display graph and stats
            styles = {'container': {'display':'block'}, 'stats': {'display':'flex'}, 'header': {'display':'flex'}}
            return (
                "Graph generated!",
                elements,
                styles['container'],
                styles['stats'],
                styles['header'],
                total,
                date_range,
                stats_date,
                days,
                devices,
                tokens,
                active_rows,
                json.dumps(manual_classifications),
                col_map_json
            )

        except Exception as err:
            # Log traceback and return error
            traceback.print_exc()
            return (
                f"Error: {err}",
                [],
                {'display':'none'},
                {'display':'none'},
                {'display':'none'},
                "0","N/A","N/A","0","0","0",[],
                no_update,
                no_update
            )

    @app.callback(
        Output('onion-graph','stylesheet', allow_duplicate=True),
        Input('onion-graph','tapNodeData'),
        State('onion-graph','elements'),
        State('onion-graph','stylesheet'),
        prevent_initial_call=True
    )
    def handle_node_tap_interaction(tap_data, elements, stylesheet):
        base = stylesheet or []
        if not tap_data or tap_data.get('is_layer_parent'):
            return base
        dynamic = list(base)
        node_id = tap_data['id']
        # Highlight tapped node and fade others
        dynamic.append({'selector': 'node', 'style': {'opacity': 0.2}})
        dynamic.append({'selector': f'node[id="{node_id}"]', 'style': {'opacity': 1, 'border-width': '3px', 'border-color': '#FFDC00'}})
        # Highlight connected edges
        dynamic.append({'selector': f'edge[source="{node_id}"]', 'style': {'opacity': 1, 'line-color': '#2ECC40', 'target-arrow-color': '#2ECC40'}})
        dynamic.append({'selector': f'edge[target="{node_id}"]', 'style': {'opacity': 1, 'line-color': '#FF4136'}})
        return dynamic

    @app.callback(
        Output('tap-node-data-output','children', allow_duplicate=True),
        Input('onion-graph','tapNodeData')
    )
    def display_tap_info(data):
        if not data or data.get('is_layer_parent'):
            return "Tap a node for details."
        info = [f"Tapped: {data.get('label', data.get('id'))}"]
        for key in ['layer','floor','is_entrance','is_stair','security_level']:
            if data.get(key) is not None:
                info.append(f"{key}: {data.get(key)}")
        return " | ".join(info)
