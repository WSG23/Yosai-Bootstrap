import pandas as pd
import numpy as np


def run_onion_model_processing(df, config, confirmed_official_entrances=None, detailed_door_classifications=None):
    """
    Enrich the raw DataFrame into onion-model components:
      - enriched_df with Date column
      - device_attrs DataFrame
      - path_viz DataFrame
      - all_paths DataFrame
    """
    # Copy and add Date
    enriched_df = df.copy()
    enriched_df['Date'] = enriched_df['Timestamp'].dt.date

    # Determine unique doors
    all_doors = enriched_df['DoorID'].unique().tolist()

    # Build device attributes
    device_attrs = []
    for i, door in enumerate(all_doors):
        detail = (detailed_door_classifications or {}).get(door, {})
        device_attrs.append({
            'DoorID': door,
            'FinalGlobalDeviceDepth': (i % 3) + 1,
            'IsOfficialEntrance': door in (confirmed_official_entrances or []),
            'IsGloballyCritical': detail.get('security') == 'Crit',
            'MostCommonNextDoor': None,
            'Floor': detail.get('floor', '1'),
            'IsStaircase': detail.get('is_stair', False),
            'SecurityLevel': detail.get('security', 'green')
        })
    device_attrs_df = pd.DataFrame(device_attrs)

    # Build path visualization data
    path_viz = []
    for i in range(len(all_doors)-1):
        path_viz.append({'Door1': all_doors[i], 'Door2': all_doors[i+1],
                         'PathWidth': np.random.randint(1,5)})
    path_viz_df = pd.DataFrame(path_viz)

    # Build all paths data
    all_paths = []
    for i in range(len(all_doors)-1):
        all_paths.append({'SourceDoor': all_doors[i], 'TargetDoor': all_doors[i+1],
                          'TransitionFrequency': np.random.randint(5,20),
                          'is_to_inner_default': (i%2==0)})
    all_paths_df = pd.DataFrame(all_paths)

    return enriched_df, device_attrs_df, path_viz_df, all_paths_df


# File: processing/cytoscape_prep.py
import pandas as pd


def prepare_cytoscape_elements(device_attrs_df, path_viz_data_df, all_paths_df):
    """
    Convert DataFrames into Cytoscape node and edge dicts.
    """
    nodes = []
    edges = []

    # Floor layers
    depths = sorted(device_attrs_df['FinalGlobalDeviceDepth'].unique())
    for d in depths:
        nodes.append({
            'data': {'id': f'layer_{d}', 'label': f'Layer {d}', 'is_layer_parent': True}
        })

    # Device nodes
    for _, row in device_attrs_df.iterrows():
        nodes.append({'data': {
            'id': row['DoorID'],
            'label': row['DoorID'],
            'parent': f"layer_{int(row['FinalGlobalDeviceDepth'])}",
            'is_entrance': bool(row['IsOfficialEntrance']),
            'is_critical': bool(row['IsGloballyCritical']),
            'security_level': row['SecurityLevel']
        }})

    # Edges
    for _, row in all_paths_df.iterrows():
        edges.append({'data': {
            'id': f"{row['SourceDoor']}_to_{row['TargetDoor']}",
            'source': row['SourceDoor'],
            'target': row['TargetDoor'],
            'width': row['TransitionFrequency'],
            'is_to_inner_default': row['is_to_inner_default']
        }})

    return nodes + edges, edges