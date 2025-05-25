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

# Modify the function signature to accept the image paths
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
            # ✅ NEW WRAPPER DIV for mapping-ui-section to center it
            html.Div(id='mapping-ui-section-wrapper', style={
                'display': 'block', # Always visible when interactive-setup-container is visible
                'width': '50%', # Adjust width as needed for centering effect
                'margin': '0 auto', # Centers the block element
                'paddingRight': '15px', # Retain padding
                'borderRight': '1px solid #ccc', # Retain border
                'boxSizing': 'border-box' # Include padding/border in width
            }, children=[
                html.Div(id='mapping-ui-section', style={'flex': 1}, children=[ # flex:1 might not be needed here anymore, but keeping for safety.
                    html.H4("Step 1: Map CSV Headers", style={'textAlign': 'center'}), # ✅ Center the H4 text
                    html.Div(id='dropdown-mapping-area'),
                    html.Button('Confirm Header Mapping & Proceed', id='confirm-header-map-button', n_clicks=0,
                                style={'marginTop': '15px', 'backgroundColor': '#007bff', 'color': 'white',
                                       'padding': '8px 12px', 'border': 'none', 'borderRadius': '4px', 'display': 'none',
                                       'marginLeft': 'auto', 'marginRight': 'auto', 'display': 'block'}) # ✅ Center the button
                ])
            ]),

            # ✅ This is now the container for Step 2 ONLY, and it needs its own display control.
            # It will be made visible by the callback when 'confirm-header-map-button' is clicked.
            html.Div(id='entrance-verification-ui-section', style={'display': 'none', 'paddingLeft': '15px', 'flex': 1}, children=[
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

            # This div was originally the flex container. We need to rethink its purpose.
            # If both Step 1 and Step 2 are part of 'interactive-setup-container',
            # and Step 2 appears AFTER Step 1, then they should be sequential DIVs inside.
            # So, the `html.Div` that had `display: 'flex', 'flexDirection': 'row'`
            # should now contain only `entrance-verification-ui-section` if mapping-ui-section is outside of it.

            # Re-evaluating the flow:
            # - Initially, 'interactive-setup-container' is hidden.
            # - 'upload-data' click makes 'interactive-setup-container' visible.
            # - 'mapping-ui-section' (Step 1) is visible by default within it.
            # - 'confirm-header-map-button' hides 'mapping-ui-section' and shows 'entrance-verification-ui-section'.
            # - 'manual-map-toggle' then shows/hides elements within 'entrance-verification-ui-section'.

            # Given this, Step 1 and Step 2 should be separate direct children
            # of 'interactive-setup-container', with their visibility managed by callbacks.

            # I am restructuring the 'interactive-setup-container' children slightly to enable this.
            # The 'mapping-ui-section' is now a direct child and can be centered.
            # The 'entrance-verification-ui-section' is also a direct child, and its visibility is controlled.
            
            # The previous flex wrapper for mapping and classification is no longer needed in that form.
            # Instead, the display:flex will apply to the direct children of interactive-setup-container if needed.
            # BUT, since they are shown sequentially, they should be simple blocks.

            # This means the `html.Div([ ... ], style={'display': 'flex', 'flexDirection': 'row'})`
            # needs to be removed, and `mapping-ui-section` and `entrance-verification-ui-section`
            # become direct children of `interactive-setup-container` (which is already `display:block` from `upload_callbacks`).

            # Let's adjust the `interactive-setup-container`'s children directly.

            # OLD structure:
            # html.Div(id='interactive-setup-container', children=[
            #     html.Div(style={'display': 'flex', 'flexDirection': 'row'}, children=[
            #         html.Div(id='mapping-ui-section', ...),
            #         html.Div(id='entrance-verification-ui-section', ...)
            #     ])
            # ])

            # NEW desired structure for sequential display:
            # html.Div(id='interactive-setup-container', children=[
            #     html.Div(id='mapping-ui-section', ...),
            #     html.Div(id='entrance-verification-ui-section', ...)
            # ])

            # Let's modify the existing 'mapping-ui-section' and 'entrance-verification-ui-section'
            # to be direct children of 'interactive-setup-container' and give mapping-ui-section centering styles.
            # The 'flex' styles on 'mapping-ui-section' and 'entrance-verification-ui-section' should also be removed
            # or replaced by explicit width/centering/display.

            # I will modify the 'mapping-ui-section' and 'entrance-verification-ui-section' directly
            # by removing the `html.Div([ ... ], style={'display': 'flex', 'flexDirection': 'row'})` wrapper.

            # Restructure: The mapping and classification UIs will be direct children of interactive-setup-container
            # Each will manage its own display style.
            # This simplifies the flow and allows independent centering of mapping-ui-section.
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
        dcc.Store(id='num-floors-store', storage_type='session', data=1),
        dcc.Store(id='all-doors-from-csv-store', storage_type='session'),
    ], style={'backgroundColor': '#EAEAEA', 'padding': '20px', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

    return layout