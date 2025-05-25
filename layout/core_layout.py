from dash import html, dcc
import dash_cytoscape as cyto
from styles.graph_styles import (
    upload_icon_img_style,
    upload_style_initial,
    centered_graph_box_style,
    cytoscape_inside_box_style,
    tap_node_data_centered_style,
    actual_default_stylesheet_for_graph
)

from config import MAIN_LOGO_PATH, ICON_UPLOAD_DEFAULT

def create_main_layout(app_instance): 
    layout = html.Div(children=[
        html.Div(style={
            'display': 'flex', 'alignItems': 'center', 'padding': '10px 20px',
            'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #dee2e6', 'marginBottom': '20px'
        }, children=[
            html.Img(src=MAIN_LOGO_PATH, style={'height': '40px', 'marginRight': '15px'}),
            html.H1("Yōsai Intel Model Dashboard", style={'fontSize': '1.8rem', 'margin': '0', 'color': '#333'})
        ]),

        dcc.Upload(
            id='upload-data',
            children=html.Img(id='upload-icon', src=ICON_UPLOAD_DEFAULT, style=upload_icon_img_style),
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
            html.Div([
                html.Div(id='mapping-ui-section', style={'flex': 1, 'paddingRight': '15px', 'borderRight': '1px solid #ccc'}, children=[
                    html.H4("Step 1: Map CSV Headers"),
                    html.Div(id='dropdown-mapping-area'),
                    html.Button('Confirm Header Mapping & Proceed', id='confirm-header-map-button', n_clicks=0,
                                style={'marginTop': '15px', 'backgroundColor': '#007bff', 'color': 'white',
                                       'padding': '8px 12px', 'border': 'none', 'borderRadius': '4px', 'display': 'none'})
                ]),
                html.Div(id='entrance-verification-ui-section', style={'flex': 1, 'paddingLeft': '15px', 'display': 'none'}, children=[
                    html.H4("Step 2: Facility & Door Classification Setup"),
                    dcc.RadioItems(id='manual-map-toggle',
                                   options=[{'label': 'Yes', 'value': 'yes'}, {'label': 'No', 'value': 'no'}],
                                   value='no', inline=True,
                                   labelStyle={'display': 'inline-block', 'marginRight': '10px'}),
                    html.Div(id='num-floors-input-container', style={'display': 'none', 'marginTop': '10px'}, children=[
                        html.Label("How many floors are in the facility? "),
                        dcc.Input(id='num-floors-input', type='number', value=1, min=1, step=1,
                                  style={'width': '60px'})
                    ]),
                    html.Div(id='door-classification-table-container', style={'display': 'none', 'marginTop': '10px'}, children=[
                        html.H5("Classify Doors (Floor, Entry/Exit, Stairway, Security Zone)"),
                        html.Div(id='door-classification-table',
                                 style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #ccc',
                                        'padding': '10px', 'backgroundColor': 'white'})
                    ]),
                    html.Div(id='entrance-suggestion-controls', style={'display': 'none', 'marginTop': '10px'}, children=[
                        html.Label("Suggestions / 'Show More' Count:", style={'marginRight': '5px'}),
                        dcc.Input(id='top-n-entrances-input', type='number', value=5, min=1, step=1,
                                  style={'width': '50px'}),
                        html.Button('Show More Potential Entrances/Exits', id='show-more-entrances-button', n_clicks=0,
                                    style={'marginLeft': '10px'})
                    ]),
                ]),
            ], style={'display': 'flex', 'flexDirection': 'row'}),

            html.Button('Confirm Selections & Generate Onion Model', id='confirm-and-generate-button', n_clicks=0,
                        style={'marginTop': '20px', 'backgroundColor': 'green', 'color': 'white',
                               'padding': '10px 15px', 'border': 'none', 'borderRadius': '5px',
                               'display': 'block', 'marginLeft': 'auto', 'marginRight': 'auto'})
        ]),

        html.Div(id='processing-status', style={'marginTop': '10px', 'color': 'blue', 'textAlign': 'center'}),

        html.Div(id='yosai-custom-header', style={
            'display': 'none', 'flexDirection': 'row', 'alignItems': 'center', 'padding': '15px 20px',
            'backgroundColor': '#ffffff', 'border': '1px solid #e0e0e0', 'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.05)', 'marginTop': '20px', 'marginBottom': '20px'
        }, children=[
            html.Img(src=MAIN_LOGO_PATH, style={'height': '40px', 'marginRight': '20px'}),
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
        dcc.Store(id='num-floors-store', storage_type='session', data=1),
        dcc.Store(id='all-doors-from-csv-store', storage_type='session'),
    ], style={'backgroundColor': '#EAEAEA', 'padding': '20px', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

    return layout
