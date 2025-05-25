# yosai_intel_dashboard/processing/cytoscape_prep.py
import pandas as pd
import numpy as np

def prepare_path_visualization_data(all_paths_df, source_col='SourceDoor',
                                    target_col='TargetDoor', frequency_col='TransitionFrequency'):
    """ Prepares path data for visualization, calculating total width for undirected paths. """
    print("\nPreparing Path Data for Visualization (in cytoscape_prep)...")
    if all_paths_df is None or all_paths_df.empty:
        print("Warning: all_paths_df is empty for path visualization.")
        return pd.DataFrame(columns=['Door1', 'Door2', 'PathWidth'])

    temp_paths_df = all_paths_df.copy()
    # Ensure source and target columns are strings for canonical pair creation
    temp_paths_df[source_col] = temp_paths_df[source_col].astype(str)
    temp_paths_df[target_col] = temp_paths_df[target_col].astype(str)

    temp_paths_df['CanonicalPair'] = temp_paths_df.apply(
        lambda row: tuple(sorted((row[source_col], row[target_col]))), axis=1
    )
    path_widths_df = temp_paths_df.groupby('CanonicalPair', observed=False)[frequency_col].sum().reset_index()
    path_widths_df.rename(columns={frequency_col: 'PathWidth'}, inplace=True)
    
    # Split CanonicalPair back into Door1 and Door2
    if not path_widths_df.empty:
        split_pairs = pd.DataFrame(path_widths_df['CanonicalPair'].tolist(), index=path_widths_df.index, columns=['Door1', 'Door2'])
        path_widths_df = pd.concat([split_pairs, path_widths_df.drop(columns=['CanonicalPair'])], axis=1)
        path_widths_df = path_widths_df[['Door1', 'Door2', 'PathWidth']] # Reorder
    else: # If path_widths_df became empty after groupby (e.g. no frequencies)
        path_widths_df = pd.DataFrame(columns=['Door1', 'Door2', 'PathWidth'])
        
    print(f"Prepared {len(path_widths_df)} unique undirected paths with widths.")
    return path_widths_df


def prepare_cytoscape_elements(device_attributes_df, path_viz_data_df, all_paths_df=None, target_floor=None):
    # ... (This function remains as it was from the last full code I provided, with floor label logic)
    # ... (Ensure it correctly uses the columns from the new device_attributes_df)
    nodes, edges = [], []
    if device_attributes_df is None or device_attributes_df.empty:
        print("DEBUG: device_attributes_df empty in prepare_cytoscape_elements.")
        return [], []

    dev_layers = {}
    if 'DoorID' in device_attributes_df.columns and 'FinalGlobalDeviceDepth' in device_attributes_df.columns:
        if 'Floor' not in device_attributes_df.columns: # defensive
            device_attributes_df['Floor'] = 'N/A'
        device_attributes_df['Floor'] = device_attributes_df['Floor'].astype(str).fillna('N/A')
        dev_layers = device_attributes_df.set_index('DoorID')['FinalGlobalDeviceDepth'].to_dict()

    dev_mcn = {}
    if 'DoorID' in device_attributes_df.columns and 'MostCommonNextDoor' in device_attributes_df.columns:
        dev_mcn = device_attributes_df.set_index('DoorID')['MostCommonNextDoor'].to_dict()

    if not device_attributes_df.empty and 'FinalGlobalDeviceDepth' in device_attributes_df.columns:
        valid_layers_depths = device_attributes_df['FinalGlobalDeviceDepth'].dropna()
        valid_layers_depths = valid_layers_depths[valid_layers_depths > 0] # Consider only positive depths
        unique_layer_depths = sorted(valid_layers_depths.unique())

        for depth_val in unique_layer_depths:
            lv_int = int(depth_val)
            devices_in_this_depth_layer = device_attributes_df[device_attributes_df['FinalGlobalDeviceDepth'] == lv_int]
            floor_label_part = ""
            if not devices_in_this_depth_layer.empty and 'Floor' in devices_in_this_depth_layer.columns:
                layer_floors = devices_in_this_depth_layer['Floor'].dropna().unique()
                layer_floors = [f for f in layer_floors if f and f.lower() != 'n/a' and f.strip() != '']
                if len(layer_floors) == 1: floor_label_part = f" (Floor {layer_floors[0]})"
                elif len(layer_floors) > 1: floor_label_part = f" (Floors: {', '.join(sorted(layer_floors))})"
            layer_parent_label = f'Layer {lv_int}{floor_label_part}'
            nodes.append({'data': {'id': f'layer_{lv_int}', 'label': layer_parent_label, 'is_layer_parent': True, 'layer_num': lv_int}})

    for _, r in device_attributes_df.iterrows():
        if 'DoorID' in r and pd.notna(r.get('FinalGlobalDeviceDepth')) and r['FinalGlobalDeviceDepth'] > 0:
            l_assign = int(r['FinalGlobalDeviceDepth'])
            door_id_str = str(r['DoorID'])
            node_data = {'id': door_id_str, 'label': door_id_str, 'layer': l_assign, 'parent': f"layer_{l_assign}",
                         'is_entrance': bool(r.get('IsOfficialEntrance', False)),
                         'is_critical': bool(r.get('IsGloballyCritical', False)),
                         'floor': str(r.get('Floor', 'N/A')),
                         'is_stair': bool(r.get('IsStaircase', False)),
                         'security_level': str(r.get('SecurityLevel', 'green'))}
            mcn_val = dev_mcn.get(r['DoorID']) # Use .get for safety
            if pd.notna(mcn_val): node_data['most_common_next'] = str(mcn_val)
            nodes.append({'data': node_data})

    if all_paths_df is not None and not all_paths_df.empty and 'SourceDoor' in all_paths_df.columns and 'TargetDoor' in all_paths_df.columns:
        w_map = {}
        if path_viz_data_df is not None and not path_viz_data_df.empty and 'Door1' in path_viz_data_df.columns and 'Door2' in path_viz_data_df.columns and 'PathWidth' in path_viz_data_df.columns:
             w_map = {(tuple(sorted((str(r['Door1']),str(r['Door2']))))): r['PathWidth'] for _,r in path_viz_data_df.iterrows()}
        
        current_device_ids = set(device_attributes_df['DoorID'].astype(str).unique())
        for _, r_edge in all_paths_df.iterrows(): # Renamed r to r_edge to avoid conflict if debugging
            s, t = str(r_edge['SourceDoor']), str(r_edge['TargetDoor'])
            if s not in current_device_ids or t not in current_device_ids: continue
            
            s_l_raw, t_l_raw = dev_layers.get(s), dev_layers.get(t)
            s_l, t_l = (int(val) if pd.notna(val) else None for val in [s_l_raw, t_l_raw])
            
            e_w_raw = w_map.get(tuple(sorted((s,t))), 1.0)
            e_w = float(e_w_raw) if pd.notna(e_w_raw) and e_w_raw > 0 else 1.0
            
            a_f_raw = r_edge.get('TransitionFrequency', 0)
            a_f = int(a_f_raw) if pd.notna(a_f_raw) else 0
            
            is_to_inner = bool(r_edge.get('is_to_inner_default', (t_l and s_l and t_l > s_l)))
            if s_l and t_l and s_l > 0 and t_l > 0:
                edges.append({'data':{'source':s,'target':t,'id':f"{s}_to_{t}_{a_f}",'width':e_w,'actual_frequency':a_f,'source_layer':s_l,'target_layer':t_l, 'is_to_inner_default': is_to_inner}})
    
    print(f"Cytoscape Prep: Prepared {len(nodes)} nodes, {len(edges)} edges.")
    return nodes, edges