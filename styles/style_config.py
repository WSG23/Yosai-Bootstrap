# style_config.py

UI_VISIBILITY = {
    'hide': {'display': 'none'},
    'show_block': {'display': 'block'},
    'show_flex_stats': {
        'display': 'flex',
        'flexDirection': 'row',
        'justifyContent': 'space-around',
        'marginBottom': '30px'
    },
    'show_header': {
        'display': 'flex',
        'flexDirection': 'row',
        'alignItems': 'center',
        'padding': '15px 20px',
        'backgroundColor': '#ffffff',
        'border': '1px solid #e0e0e0',
        'borderRadius': '8px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
        'marginTop': '20px',
        'marginBottom': '20px'
    }
}

UI_COMPONENTS = {
    'table_cell_right': {'textAlign': 'right'},
    'table_na_row': {'colSpan': 2},
    'font_default': {'fontFamily': 'Arial, sans-serif'},
    'default_container': {
        'backgroundColor': '#EAEAEA',
        'padding': '20px',
        'minHeight': '100vh'
    }
}
