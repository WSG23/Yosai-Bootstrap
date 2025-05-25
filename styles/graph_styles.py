# yosai_intel_dashboard/styles.py

# --- Styles for the Upload Box ---
upload_box_base_style = {
    'width': '120px', 'height': '120px', 'borderWidth': '3px', 'borderStyle': 'solid',
    'borderRadius': '20px', 'margin': '20px auto', 'backgroundColor': '#f0f2f5',
    'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'cursor': 'pointer',
    'transition': 'border-color 0.3s ease-in-out, background-color 0.3s ease-in-out'
}
upload_style_initial = {**upload_box_base_style, 'borderColor': '#a0a0a0'}
upload_style_success = {**upload_box_base_style, 'borderColor': '#28a745', 'backgroundColor': '#e9f5e9'}
upload_style_fail = {**upload_box_base_style, 'borderColor': '#dc3545', 'backgroundColor': '#fdecea'}
upload_icon_img_style = {'height': '60px', 'width': '60px', 'objectFit': 'contain'}

# --- Cytoscape Stylesheets ---
diagnostic_stylesheet = [
    {'selector': 'node', 'style': {'label': 'data(label)', 'font-size': '10px', 'color': 'black', 'text-outline-color': '#FFFFFF', 'text-outline-width': '1px'}},
    {'selector': 'node[?is_layer_parent]', 'style': {
        'background-color': 'rgba(0, 255, 0, 0.2)', 'border-width': '2px', 'border-style': 'solid', 'border-color': 'darkgreen',
        'shape': 'round-rectangle', 'width': '50px', 'height': '50px', 'padding': '40px'}},
    {'selector': 'node[!is_layer_parent]', 'style': {
        'background-color': '#FFFF00', 'width': '20px', 'height': '20px', 'border-width': '1px', 'border-color': 'black'}},
    {'selector': 'node[?is_entrance][!is_layer_parent]', 'style': {'background-color': '#00FF00'}},
    {'selector': 'node[?is_critical][!is_layer_parent]', 'style': {'background-color': '#FF00FF', 'shape':'star'}},
    {'selector': "node[most_common_next][!is_layer_parent]", 'style': {'border-color': '#FFD700', 'border-width': '3px'}},
    {'selector': 'edge', 'style': {
        'display': 'element', 'line-color': 'blue', 'width': 1, 'opacity': 0.7,
        'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'arrow-scale': 0.8, 'target-arrow-color': 'blue'}}
]

actual_default_stylesheet_for_graph = [
   {'selector': 'node[?is_layer_parent]', 'style': {
        'background-opacity': 0.05, 'background-color': '#f0f0f0', 'border-width': '2px',
        'border-style': 'solid', 'border-color': 'black', 'shape': 'round-rectangle',
        'label': 'data(label)', 'font-size': '13px',
        'color': '#333333', 'text-halign':'center', 'text-valign':'top',
        'text-margin-y': -15, 'z-compound-depth': 'bottom', 'padding': '40px'}},
    {'selector': 'node[!is_layer_parent]', 'style': {'label': 'data(label)', 'background-color': '#888', 'width': '25px', 'height': '25px', 'font-size': '10px', 'opacity': 1, 'border-width': '0px', 'z-compound-depth': 'top'}},
    {'selector': 'node[?is_entrance][!is_layer_parent]', 'style': {'background-color': '#2ECC40', 'shape': 'diamond'}},
    {'selector': 'node[?is_critical][!is_layer_parent]', 'style': {'background-color': '#FF4136', 'shape': 'star', 'width':'35px', 'height':'35px'}},
    {'selector': "node[most_common_next][!is_layer_parent]", 'style': {'background-color': '#FFDC00'}},
    {'selector': 'edge', 'style': {'display': 'none', 'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'arrow-scale': 1, 'line-color': '#ccc', 'target-arrow-color': '#ccc', 'width': 'data(width)'}},
    {'selector': 'edge[?is_to_inner_default]', 'style': {'display': 'element', 'opacity': 0.6}}
]

# --- Styles for Centered Graph Box ---
centered_graph_box_style = {
    'width': '85%', 'maxWidth': '1200px', 'height': '650px', 'margin': '20px auto',
    'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '8px',
    'boxShadow': '0 4px 12px rgba(0,0,0,0.1)', 'backgroundColor': '#ffffff', 'overflow': 'hidden'
}
cytoscape_inside_box_style = {
    'width': '100%', 'height': '100%', 'border': '1px solid #e0e0e0', 'borderRadius': '5px'
}
tap_node_data_centered_style = {
    'width': '85%', 'maxWidth': '1200px', 'margin': '20px auto', 'border': 'thin #ccc solid',
    'overflowX': 'scroll', 'padding':'10px', 'backgroundColor':'#f9f9f9', 'color':'#333', 'borderRadius': '5px'
}