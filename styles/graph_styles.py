# styles/graph_styles.py
# ✅ Import COLORS from your updated style_config
from styles.style_config import COLORS

upload_icon_img_style = {
    'width': '100px', 'height': '100px', 'cursor': 'pointer',
    'transition': 'transform 0.2s ease-in-out',
    # Adjust this filter or remove it if your icon assets are pre-colored for dark theme
    'filter': 'brightness(1.5) saturate(0.5) hue-rotate(180deg) opacity(0.8)' # Example filter for light icon on dark background
}

upload_style_initial = {
    'width': '95%',
    'height': '150px',
    'lineHeight': '150px',
    'borderWidth': '2px',
    'borderStyle': 'dashed',
    'borderRadius': '10px',
    'textAlign': 'center',
    'margin': '20px auto',
    'display': 'block',
    'backgroundColor': COLORS['surface'], # Use 'surface'
    'borderColor': COLORS['border'], # Use 'border'
    'color': COLORS['text_light'] # Use 'text_light' for text
}

upload_style_success = {
    'width': '95%',
    'height': '150px',
    'lineHeight': '150px',
    'borderWidth': '2px',
    'borderStyle': 'solid',  # Solid border for success
    'borderRadius': '10px',
    'textAlign': 'center',
    'margin': '20px auto',
    'display': 'block',
    'backgroundColor': COLORS['surface'], # Keep surface or make slightly green
    'borderColor': COLORS['success'],   # Green border for success
    'color': COLORS['success']          # Green text for success
}

upload_style_fail = {
    'width': '95%',
    'height': '150px',
    'lineHeight': '150px',
    'borderWidth': '2px',
    'borderStyle': 'solid',  # Solid border for failure
    'borderRadius': '10px',
    'textAlign': 'center',
    'margin': '20px auto',
    'display': 'block',
    'backgroundColor': COLORS['surface'], # Keep surface or make slightly red
    'borderColor': COLORS['critical'],  # Red border for failure
    'color': COLORS['critical']         # Red text for failure
}


centered_graph_box_style = {
    'border': f'1px solid {COLORS["border"]}', # Use 'border'
    'borderRadius': '8px',
    'boxShadow': '0 4px 8px rgba(0,0,0,0.2)', # Darker shadow for dark theme
    'backgroundColor': COLORS['surface'], # Use 'surface'
    'padding': '15px',
    'width': '95%',
    'height': '600px',
    'margin': '20px auto',
    'display': 'flex',
    'justifyContent': 'center',
    'alignItems': 'center'
}

cytoscape_inside_box_style = {
    'width': '100%',
    'height': '100%'
}

tap_node_data_centered_style = {
    'width': '95%',
    'margin': '10px auto 30px auto',
    'padding': '15px',
    'border': f'1px solid {COLORS["border"]}', # Use 'border'
    'borderRadius': '5px',
    'backgroundColor': COLORS['surface'], # Use 'surface'
    'boxShadow': '0 2px 4px rgba(0,0,0,0.2)', # Darker shadow for dark theme
    'whiteSpace': 'pre-wrap',
    'textAlign': 'center',
    'fontSize': '0.9em',
    'color': COLORS['text_dark'] # Use 'text_dark'
}

actual_default_stylesheet_for_graph = [
    # NODE STYLES
    {
        'selector': 'node',
        'style': {
            'background-color': COLORS['primary'], # Use 'primary' for default nodes
            'label': 'data(label)',
            'font-size': '10px',
            'color': COLORS['text_on_dark'], # Text on dark nodes
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 'mapData(weight, 0, 100, 20, 60)',
            'height': 'mapData(weight, 0, 100, 20, 60)',
            'border-color': COLORS['border'], # Node border
            'border-width': 1,
        }
    },
    # EDGE STYLES
    {
        'selector': 'edge',
        'style': {
            'line-color': COLORS['border'], # Use 'border' for edges
            'width': 1,
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': COLORS['border']
        }
    },
    # Specific styles for security levels (these MUST match your COLORS and SECURITY_LEVELS_SLIDER_MAP)
    {
        'selector': '[security_level="unclassified"]',
        'style': {'background-color': COLORS['border'], 'border-color': COLORS['border'], 'color': COLORS['text_dark']} # Use dark text on this lighter color
    },
    {
        'selector': '[security_level="green"]',
        'style': {'background-color': COLORS['success'], 'border-color': COLORS['success'], 'color': COLORS['text_on_dark']}
    },
    {
        'selector': '[security_level="yellow"]', # This is 'orange' in your map
        'style': {'background-color': COLORS['warning'], 'border-color': COLORS['warning'], 'color': COLORS['text_on_dark']}
    },
    {
        'selector': '[security_level="red"]',
        'style': {'background-color': COLORS['critical'], 'border-color': COLORS['critical'], 'color': COLORS['text_on_dark']}
    },
    # Add other selectors as needed for active, selected states etc.
    {
        'selector': ':selected',
        'style': {
            'border-width': 2,
            'border-color': COLORS['accent'], # Highlight selected items with accent color
            'overlay-padding': 3,
            'overlay-color': COLORS['accent'],
            'overlay-opacity': 0.2
        }
    }
]