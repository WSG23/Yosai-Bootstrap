from dash import html, dcc
import dash_cytoscape as cyto

# Asset URLs will be generated via app.get_asset_url in build_layout

def build_layout(app):
    ICON_UPLOAD_DEFAULT = app.get_asset_url('upload_file_csv_icon.png')
    upload_box_style = {'width': '120px', 'height': '120px', 'borderWidth': '3px',
                        'borderStyle': 'solid', 'borderRadius': '20px', 'margin': '20px auto',
                        'backgroundColor': '#f0f2f5', 'display': 'flex',
                        'justifyContent': 'center', 'alignItems': 'center', 'cursor': 'pointer'}

    return html.Div([
        # Upload Component
        dcc.Upload(
            id='upload-data',
            children=html.Img(id='upload-icon', src=ICON_UPLOAD_DEFAULT,
                              style={'height': '60px', 'width': '60px'}),
            style=upload_box_style,
            multiple=False,
            accept='.csv'
        ),
        html.Div(id='upload-status-text', style={'textAlign':'center', 'marginTop':'10px'}),

        # Placeholder for header-mapping UI
        html.Div(id='mapping-ui-container', style={'display':'none'}),

        # Graph Output
        html.Div(id='graph-output-container', style={'display':'none', 'marginTop':'20px'}, children=[
            cyto.Cytoscape(
                id='onion-graph',
                layout={'name': 'cose'},
                style={'width': '100%', 'height': '500px'},
                elements=[],
                stylesheet=[]
            )
        ])
    ], style={'padding':'20px', 'fontFamily':'Arial, sans-serif'})