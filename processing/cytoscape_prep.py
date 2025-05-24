def prepare_cytoscape_elements(device_attrs_df, path_viz_data_df, all_paths_df):
    nodes, edges = [], []
    depths = sorted(device_attrs_df['FinalGlobalDeviceDepth'].unique())
    for d in depths:
        nodes.append({'data': {'id': f'layer_{d}', 'label': f'Layer {d}', 'is_layer_parent': True}})
    for _, row in device_attrs_df.iterrows():
        nodes.append({'data': {
            'id': row['DoorID'], 'label': row['DoorID'],
            'parent': f"layer_{int(row['FinalGlobalDeviceDepth'])}",
            'is_entrance': bool(row['IsOfficialEntrance']),
            'is_critical': bool(row['IsGloballyCritical']),
            'security_level': row['SecurityLevel']
        }})
    for _, row in all_paths_df.iterrows():
        edges.append({'data': {
            'id': f"{row['SourceDoor']}_to_{row['TargetDoor']}", 'source': row['SourceDoor'],
            'target': row['TargetDoor'], 'width': row['TransitionFrequency'],
            'is_to_inner_default': row['is_to_inner_default']
        }})
    return nodes + edges, edges