# layout/core_layout.py
from dash import html, dcc
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc

# ✅ Import COLORS from your updated style_config
from styles.style_config import COLORS, UI_VISIBILITY, UI_COMPONENTS
from styles.graph_styles import (
    upload_icon_img_style,
    upload_style_initial,
    centered_graph_box_style,
    cytoscape_inside_box_style,
    tap_node_data_centered_style,
    actual_default_stylesheet_for_graph
)

# Define Security Levels for the slider (MUST BE CONSISTENT)
# Updated to use your new color scheme for security levels
SECURITY_LEVELS_SLIDER_MAP = {
    0: {"label": "⬜️ Unclassified", "color": COLORS['border'], "value": "unclassified"}, # Using Border for unclassified
    1: {"label": "🟢 Green (Public)", "color": COLORS['success'], "value": "green"},
    2: {"label": "🟠 Orange (Semi-Restricted)", "color": COLORS['warning'], "value": "yellow"}, # Mapped to 'yellow' for internal logic
    3: {"label": "🔴 Red (Restricted)", "color": COLORS['critical'], "value": "red"},
}

def create_main_layout(app_instance, main_logo_path, icon_upload_default):
    layout = html.Div(children=[
        # Main Header Bar
        html.Div(style={
            'display': 'flex', 'alignItems': 'center', 'padding': '10px 20px',
            'backgroundColor': COLORS['surface'], # Use 'surface' for header background
            'borderBottom': f'1px solid {COLORS["border"]}', # Use 'border'
            'marginBottom': '20px'
        }, children=[
            html.Img(src=main_logo_path, style={'height': '40px', 'marginRight': '15px'}),
            html.H1("Yōsai Intel Model Dashboard", style={'fontSize': '1.8rem', 'margin': '0', 'color': COLORS['text_dark']}) # Use 'text_dark' for header text
        ]),

        dcc.Upload(
            id='upload-data',
            children=html.Img(id='upload-icon', src=icon_upload_default, style=upload_icon_img_style),
            style=upload_style_initial, # This is from graph_styles.py, will update there
            multiple=False,
            accept='.csv'
        ),

        html.Div(id='upload-status-text', children="Please upload a CSV file.",
                 style={'textAlign': 'center', 'marginBottom': '10px', 'fontSize': '0.9em', 'color': COLORS['text_light']}), # Use 'text_light'

        html.Div(id='interactive-setup-container', style={
            'display': 'none', 'padding': '15px',
            'backgroundColor': COLORS['surface'], # Use 'surface' for this section's background
            'borderRadius': '5px',
            'margin': '20px auto', 'width': '95%',
            'boxShadow': '0 4px 8px rgba(0,0,0,0.2)' # Add shadow for distinction in dark theme
        }, children=[
            # Step 1: Map CSV Headers - Centered
            html.Div(id='mapping-ui-section', style={
                'display': 'block',
                'width': '50%',
                'margin': '0 auto',
                'paddingRight': '15px',
                'borderRight': f'1px solid {COLORS["border"]}', # Use 'border'
                'boxSizing': 'border-box'
            }, children=[
                html.H4("Step 1: Map CSV Headers", className="text-center", style={'color': COLORS['text_dark']}), # Use 'text_dark' for H4
                html.Div(id='dropdown-mapping-area'),
                html.Button('Confirm Header Mapping & Proceed', id='confirm-header-map-button', n_clicks=0,
                            style={'marginTop': '15px', 'backgroundColor': COLORS['accent'], 'color': COLORS['text_on_dark'], # Use 'accent' and 'text_on_dark'
                                   'padding': '8px 12px', 'border': 'none', 'borderRadius': '4px',
                                   'marginLeft': 'auto', 'marginRight': 'auto', 'display': 'block'})
            ]),

            # ✅ NEW STRUCTURE FOR STEP 2 (Facility Setup) and Step 3 (Door Classification)
            dbc.Container(id='entrance-verification-ui-section', fluid=True,
                          style={'display': 'none', 'padding': '0', 'margin': '0 auto', 'textAlign': 'center'}, children=[

                # ─────────────── Step 2: Facility Setup ───────────────
                dbc.Card([
                    dbc.CardHeader(html.H4("Step 2: Facility Setup", className="text-center", style={'color': COLORS['text_dark']})), # Use 'text_dark'
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("How many floors are in the facility?", className="fw-bold", style={'color': COLORS['text_dark']}), # Use 'text_dark'
                                dcc.Dropdown(
                                    id="num-floors-input",
                                    options=[{"label": str(i), "value": i} for i in range(1, 11)],
                                    value=3,
                                    clearable=False,
                                    style={"width": "100%", "marginBottom": "0.5rem",
                                           'backgroundColor': COLORS['background'], 'color': COLORS['text_dark'], 'borderColor': COLORS['border']} # Apply colors to dropdown
                                ),
                                html.Small("Count floors above ground including mezzanines and secure zones.", className="text-muted", style={'color': COLORS['text_light']}) # Use 'text_light'
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Enable Manual Door Classification?", className="fw-bold", style={'color': COLORS['text_dark']}), # Use 'text_dark'
                                dcc.RadioItems(
                                    id='manual-map-toggle',
                                    options=[{'label': 'Yes', 'value': 'yes'}, {'label': 'No', 'value': 'no'}],
                                    value='no', inline=True,
                                    labelStyle={'display': 'inline-block', 'marginRight': '10px', 'color': COLORS['text_dark']}, # Use 'text_dark'
                                    className="my-2"
                                ),
                            ])
                        ])
                    ])
                ], className="shadow-sm p-4 my-4 rounded", style={'backgroundColor': COLORS['surface']}), # Use 'surface' for card background

                # ─────────────── Step 3: Door Classification (conditional visibility) ───────────────
                dbc.Card(id="door-classification-table-container",
                    style={'display': 'none', 'backgroundColor': COLORS['surface']}, # Use 'surface' for card background
                    children=[
                        dbc.CardHeader(html.H4("Step 3: Door Classification", className="text-center", style={'color': COLORS['text_dark']})), # Use 'text_dark'
                        dbc.CardBody([
                            html.P("Assign a security level to each door below:", className="mb-4 fw-bold", style={'color': COLORS['text_dark']}), # Use 'text_dark'
                            html.Div(id="door-classification-table"),
                            html.Br(),
                            html.Div(id='entrance-suggestion-controls', style={'display': 'none', 'marginTop': '10px'}, children=[
                                html.Label("Suggestions / 'Show More' Count:", style={'marginRight': '5px', 'color': COLORS['text_dark']}), # Use 'text_dark'
                                dcc.Input(id='top-n-entrances-input', type='number', value=5, min=1, step=1,
                                        style={'width': '50px', 'backgroundColor': COLORS['background'], 'color': COLORS['text_dark'], 'borderColor': COLORS['border']}), # Apply colors
                                html.Button('Show More Potential Entrances/Exits', id='show-more-entrances-button', n_clicks=0,
                                            style={'marginLeft': '10px'}) # Button styles will be inherited from Bootstrap theme
                            ]),
                            dbc.Button("Show More Selection & Continue → Step 4", id="continue-btn", color="primary", className="w-100") # Bootstrap primary color
                        ])
                    ], className="shadow-sm p-4 my-4 rounded"),
            ]),

            # The final "Confirm Selections & Generate" button
            html.Button('Confirm Selections & Generate Onion Model', id='confirm-and-generate-button', n_clicks=0,
                        style={'marginTop': '20px', 'backgroundColor': COLORS['success'], 'color': COLORS['text_on_dark'], # Use 'success' and 'text_on_dark'
                               'padding': '10px 15px', 'border': 'none', 'borderRadius': '5px',
                               'display': 'block', 'marginLeft': 'auto', 'marginRight': 'auto'})
        ]), # Close interactive-setup-container


        html.Div(id='processing-status', style={'marginTop': '10px', 'color': COLORS['accent'], 'textAlign': 'center'}), # Use 'accent'

        # Using the style dict from style_config directly
        html.Div(id='yosai-custom-header', style=UI_VISIBILITY['show_header'], children=[
            html.Img(src=main_logo_path, style={'height': '40px', 'marginRight': '20px'}),
            html.Div([
                html.H1("Yōsai Intel", style={'margin': '0 0 2px 0', 'fontSize': '1.8rem', 'color': COLORS['primary'], 'fontWeight': 'bold'}), # Use 'primary'
                html.P("Data Overview", style={'margin': '0', 'fontSize': '1.1rem', 'color': COLORS['text_light']}) # Use 'text_light'
            ]),
        ]),

        # Using the style dict from style_config directly
        html.Div(id='stats-panels-container', style=UI_VISIBILITY['show_flex_stats'], children=[
            html.Div([html.H3("Access events", style={'color': COLORS['text_dark']}), html.H1(id="total-access-events-H1", style={'color': COLORS['text_dark']}), html.P(id="event-date-range-P", style={'color': COLORS['text_light']})], style={ # Text colors
                'flex': '1', 'padding': '20px', 'margin': '0 10px',
                'backgroundColor': COLORS['surface'], # Use 'surface'
                'borderRadius': '8px', 'textAlign': 'center',
                'borderLeft': f'5px solid {COLORS["accent"]}', # Use 'accent' for left border
                'boxShadow': '2px 2px 5px rgba(0,0,0,0.2)'}), # Soft shadow for dark theme
            html.Div([html.H3("Statistics", style={'color': COLORS['text_dark']}), html.P(id="stats-date-range-P", style={'color': COLORS['text_light']}), html.P(id="stats-days-with-data-P", style={'color': COLORS['text_light']}), html.P(id="stats-num-devices-P", style={'color': COLORS['text_light']}), html.P(id="stats-unique-tokens-P", style={'color': COLORS['text_light']})], style={ # Text colors
                'flex': '1', 'padding': '20px', 'margin': '0 10px',
                'backgroundColor': COLORS['surface'], # Use 'surface'
                'borderRadius': '8px',
                'borderLeft': f'5px solid {COLORS["warning"]}', # Use 'warning' for left border
                'boxShadow': '0 2px 5px rgba(0,0,0,0.2)'}),
            html.Div([html.H3("Most active devices", style={'color': COLORS['text_dark']}), html.Table([ # Text colors
                html.Thead(html.Tr([html.Th("DEVICE", style={'color': COLORS['text_dark']}), html.Th("EVENTS", style={'color': COLORS['text_dark']})])), # Table header text
                html.Tbody(id='most-active-devices-table-body')
            ])], style={
                'flex': '1', 'padding': '20px', 'margin': '0 10px',
                'backgroundColor': COLORS['surface'], # Use 'surface'
                'borderRadius': '8px',
                'borderLeft': f'5px solid {COLORS["critical"]}', # Use 'critical' for left border
                'boxShadow': '0 2px 5px rgba(0,0,0,0.2)'}),
        ]),

        html.Div(id='graph-output-container', style={'display': 'none'}, children=[
            html.H2("Area Layout Model", id="area-layout-model-title", style={'textAlign': 'center', 'color': COLORS['text_dark'], 'marginBottom': '20px', 'fontSize': '1.8rem'}), # Use 'text_dark'
            html.Div(id='cytoscape-graphs-area', style=centered_graph_box_style, children=[ # From graph_styles.py
                cyto.Cytoscape(
                    id='onion-graph',
                    layout={'name': 'cose', 'idealEdgeLength': 100, 'nodeOverlap': 20, 'refresh': 20, 'fit': True, 'padding': 30, 'randomize': False, 'componentSpacing': 100, 'nodeRepulsion': 400000, 'edgeElasticity': 100, 'nestingFactor': 5, 'gravity': 80, 'numIter': 1000, 'coolingFactor': 0.95, 'minTemp': 1.0},
                    style=cytoscape_inside_box_style, # From graph_styles.py
                    elements=[],
                    stylesheet=actual_default_stylesheet_for_graph
                )
            ]),
            html.Pre(id='tap-node-data-output', style=tap_node_data_centered_style) # From graph_styles.py
        ]),

        dcc.Store(id='uploaded-file-store'),
        dcc.Store(id='csv-headers-store', storage_type='session'),
        dcc.Store(id='column-mapping-store', storage_type='local'),
        dcc.Store(id='ranked-doors-store', storage_type='session'),
        dcc.Store(id='current-entrance-offset-store', data=0, storage_type='session'),
        dcc.Store(id='manual-door-classifications-store', storage_type='local'),
        dcc.Store(id='num-floors-store', storage_type='session', data=1),
        dcc.Store(id='all-doors-from-csv-store', storage_type='session'),
    ], style={'backgroundColor': COLORS['background'], 'padding': '20px', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'}) # Use new 'background'

    return layout