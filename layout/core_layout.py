from dash import html, dcc
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc # ✅ NEW IMPORT

from styles.graph_styles import (
    upload_icon_img_style,
    upload_style_initial,
    centered_graph_box_style,
    cytoscape_inside_box_style,
    tap_node_data_centered_style,
    actual_default_stylesheet_for_graph
)

# Define Security Levels for the slider (MUST BE CONSISTENT)
# This mapping needs to be available where the layout is created and where callbacks process it.
SECURITY_LEVELS_SLIDER_MAP = {
    0: {"label": "⬜️ Unclassified", "color": "#CCCCCC", "value": "unclassified"}, # Added "value" for internal consistency
    1: {"label": "🟢 Green (Public)", "color": "#27AE60", "value": "green"},
    2: {"label": "🟠 Orange (Semi-Restricted)", "color": "#F39C12", "value": "yellow"}, # Mapped to 'yellow'
    3: {"label": "🔴 Red (Restricted)", "color": "#C0392B", "value": "red"},
}


def create_main_layout(app_instance, main_logo_path, icon_upload_default): 
    layout = html.Div(children=[
        html.Div(style={
            'display': 'flex', 'alignItems': 'center', 'padding': '10px 20px',
            'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #dee2e6', 'marginBottom': '20px'
        }, children=[
            html.Img(src=main_logo_path, style={'height': '40px', 'marginRight': '15px'}),
            html.H1("Yōsai Intel Model Dashboard", style={'fontSize': '1.8rem', 'margin': '0', 'color': '#333'})
        ]),

        dcc.Upload(
            id='upload-data',
            children=html.Img(id='upload-icon', src=icon_upload_default, style=upload_icon_img_style),
            style=upload_style_initial,
            multiple=False,
            accept='.csv'
        ),

        html.Div(id='upload-status-text', children="Please upload a CSV file.",
                 style={'textAlign': 'center', 'marginBottom': '10px', 'fontSize': '0.9em', 'color': '#555'}),

        html.Div(id='interactive-setup-container', style={
            'display': 'none', 'padding': '15px', 'backgroundColor': '#e9e9e9', 'borderRadius': '5px',
            'margin': '20px auto', 'width': '95%'
        }, children=[
            # Step 1: Map CSV Headers - Centered
            html.Div(id='mapping-ui-section', style={
                'display': 'block',
                'width': '50%',
                'margin': '0 auto',
                'paddingRight': '15px',
                'borderRight': '1px solid #ccc',
                'boxSizing': 'border-box'
            }, children=[ 
                html.H4("Step 1: Map CSV Headers", className="text-center"), # Use dbc for styling
                html.Div(id='dropdown-mapping-area'),
                html.Button('Confirm Header Mapping & Proceed', id='confirm-header-map-button', n_clicks=0,
                            style={'marginTop': '15px', 'backgroundColor': '#007bff', 'color': 'white',
                                   'padding': '8px 12px', 'border': 'none', 'borderRadius': '4px',
                                   'marginLeft': 'auto', 'marginRight': 'auto', 'display': 'block'})
            ]),

            # ✅ NEW STRUCTURE FOR STEP 2 (Facility Setup) and Step 3 (Door Classification)
            # This is the container that will be toggled by the mapping_callbacks
            dbc.Container(id='entrance-verification-ui-section', fluid=True, # fluid=True makes it 100% width of parent
                          style={'display': 'none', 'padding': '0', 'margin': '0 auto', 'textAlign': 'center'}, children=[ 
                
                # ─────────────── Step 2: Facility Setup ───────────────
                dbc.Card([
                    dbc.CardHeader(html.H4("Step 2: Facility Setup", className="text-center")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("How many floors are in the facility?", className="fw-bold"),
                                dcc.Dropdown(
                                    id="num-floors-input", # Keep original ID for callback compatibility
                                    options=[{"label": str(i), "value": i} for i in range(1, 11)], # Up to 10 floors
                                    value=3, # Default value
                                    clearable=False,
                                    style={"width": "100%", "marginBottom": "0.5rem"}
                                ),
                                html.Small("Count floors above ground including mezzanines and secure zones.", className="text-muted")
                            ])
                        ]),
                        # The manual-map-toggle and entrance-suggestion-controls were here.
                        # We need to decide where to place them in this new DBC Card structure.
                        # For now, let's place manual-map-toggle here, as it pertains to setup.
                        dbc.Row([
                            dbc.Col([
                                html.Label("Enable Manual Door Classification?", className="fw-bold"),
                                dcc.RadioItems(
                                    id='manual-map-toggle',
                                    options=[{'label': 'Yes', 'value': 'yes'}, {'label': 'No', 'value': 'no'}],
                                    value='no', inline=True,
                                    labelStyle={'display': 'inline-block', 'marginRight': '10px'},
                                    className="my-2"
                                ),
                            ])
                        ])
                    ])
                ], className="shadow-sm p-4 my-4 bg-white rounded"), # End Step 2 Card

                # ─────────────── Step 3: Door Classification (conditional visibility) ───────────────
                # This entire card will be controlled by manual-map-toggle
                dbc.Card(id="door-classification-table-container", # Keep original ID for callback compatibility
                    style={'display': 'none'}, # Initially hidden, revealed by toggle_classification_tools
                    children=[
                        dbc.CardHeader(html.H4("Step 3: Door Classification", className="text-center")),
                        dbc.CardBody([
                            html.P("Assign a security level to each door below:", className="mb-4 fw-bold"),
                            html.Div(id="door-classification-table"), # This will contain the generated rows
                            html.Br(),
                            # Original entrance-suggestion-controls content will go here if needed
                            html.Div(id='entrance-suggestion-controls', style={'display': 'none', 'marginTop': '10px'}, children=[
                                html.Label("Suggestions / 'Show More' Count:", style={'marginRight': '5px'}),
                                dcc.Input(id='top-n-entrances-input', type='number', value=5, min=1, step=1,
                                        style={'width': '50px'}),
                                html.Button('Show More Potential Entrances/Exits', id='show-more-entrances-button', n_clicks=0,
                                            style={'marginLeft': '10px'})
                            ]),
                            # The continue button from your sample
                            dbc.Button("Show More Selection & Continue → Step 4", id="continue-btn", color="primary", className="w-100")
                        ])
                    ], className="shadow-sm p-4 my-4 bg-white rounded"), # End Step 3 Card
            ]), # End entrance-verification-ui-section container
            
            # The final "Confirm Selections & Generate" button
            html.Button('Confirm Selections & Generate Onion Model', id='confirm-and-generate-button', n_clicks=0,
                        style={'marginTop': '20px', 'backgroundColor': 'green', 'color': 'white',
                               'padding': '10px 15px', 'border': 'none', 'borderRadius': '5px',
                               'display': 'block', 'marginLeft': 'auto', 'marginRight': 'auto'})
        ]), # Close interactive-setup-container


        html.Div(id='processing-status', style={'marginTop': '10px', 'color': 'blue', 'textAlign': 'center'}),

        html.Div(id='yosai-custom-header', style={
            'display': 'none', 'flexDirection': 'row', 'alignItems': 'center', 'padding': '15px 20px',
            'backgroundColor': '#ffffff', 'border': '1px solid #e0e0e0', 'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.05)', 'marginTop': '20px', 'marginBottom': '20px'
        }, children=[
            html.Img(src=main_logo_path, style={'height': '40px', 'marginRight': '20px'}),
            html.Div([
                html.H1("Yōsai Intel", style={'margin': '0 0 2px 0', 'fontSize': '1.8rem', 'color': '#333366', 'fontWeight': 'bold'}),
                html.P("Data Overview", style={'margin': '0', 'fontSize': '1.1rem', 'color': '#555'})
            ]),
        ]),

        html.Div(id='stats-panels-container', style={'display': 'none', 'flexDirection': 'row', 'justifyContent': 'space-around', 'marginTop': '0px', 'marginBottom': '30px'}, children=[
            html.Div([html.H3("Access events"), html.H1(id="total-access-events-H1"), html.P(id="event-date-range-P")], style={'flex': '1', 'padding': '20px', 'margin': '0 10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'textAlign': 'center', 'borderLeft': '5px solid #E91E63', 'boxShadow': '2px 2px 5px #ccc'}),
            html.Div([html.H3("Statistics"), html.P(id="stats-date-range-P"), html.P(id="stats-days-with-data-P"), html.P(id="stats-num-devices-P"), html.P(id="stats-unique-tokens-P")], style={'flex': '1', 'padding': '20px', 'margin': '0 10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'borderLeft': '5px solid #673AB7', 'boxShadow': '2px 2px 5px #ccc'}),
            html.Div([html.H3("Most active devices"), html.Table([
                html.Thead(html.Tr([html.Th("DEVICE"), html.Th("EVENTS")])),
                html.Tbody(id='most-active-devices-table-body')
            ])], style={'flex': '1', 'padding': '20px', 'margin': '0 10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'borderLeft': '5px solid #2196F3', 'boxShadow': '2px 2px 5px #ccc'}),
        ]),

        html.Div(id='graph-output-container', style={'display': 'none'}, children=[
            html.H2("Area Layout Model", id="area-layout-model-title", style={'textAlign': 'center', 'color': '#333', 'marginBottom': '20px', 'fontSize': '1.8rem'}),
            html.Div(id='cytoscape-graphs-area', style=centered_graph_box_style, children=[
                cyto.Cytoscape(
                    id='onion-graph',
                    layout={'name': 'cose', 'idealEdgeLength': 100, 'nodeOverlap': 20, 'refresh': 20, 'fit': True, 'padding': 30, 'randomize': False, 'componentSpacing': 100, 'nodeRepulsion': 400000, 'edgeElasticity': 100, 'nestingFactor': 5, 'gravity': 80, 'numIter': 1000, 'initialTemp': 200, 'coolingFactor': 0.95, 'minTemp': 1.0},
                    style=cytoscape_inside_box_style,
                    elements=[],
                    stylesheet=actual_default_stylesheet_for_graph
                )
            ]),
            html.Pre(id='tap-node-data-output', style=tap_node_data_centered_style)
        ]),

        dcc.Store(id='uploaded-file-store'),
        dcc.Store(id='csv-headers-store', storage_type='session'),
        dcc.Store(id='column-mapping-store', storage_type='local'),
        dcc.Store(id='ranked-doors-store', storage_type='session'),
        dcc.Store(id='current-entrance-offset-store', data=0, storage_type='session'),
        dcc.Store(id='manual-door-classifications-store', storage_type='local'),
        dcc.Store(id='num-floors-store', storage_type='session', data=1), # Keep original ID
        dcc.Store(id='all-doors-from-csv-store', storage_type='session'),
    ], style={'backgroundColor': '#EAEAEA', 'padding': '20px', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

    return layout