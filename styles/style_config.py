# styles/style_config.py

# --- Universal Color Palette (Dark Theme) ---
# Your new, redefined dark theme colors.
COLORS = {
    "primary": "#1B2A47",       # Deep navy (main brand color)
    "accent": "#2196F3",        # Bright blue accent
    "success": "#2DBE6C",       # Green for positive status
    "warning": "#FFB020",       # Amber for warnings
    "critical": "#E02020",      # Red for errors/alerts
    "background": "#121A2B",    # Very dark blue-black for background
    "surface": "#232F44",       # Slightly lighter card/overlay
    "border": "#293656",        # Muted navy for lines and borders
    "text_dark": "#F4F6F8",     # Light text for dark backgrounds (main text)
    "text_light": "#B8C1D4",    # Muted blue-grey for secondary text
    "text_on_dark": "#FFFFFF",  # Pure white text for extreme contrast on dark colors like primary/accent
}


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
        'padding': '10px 20px',
        'backgroundColor': COLORS['surface'], # Using new 'surface' color
        'borderBottom': f'1px solid {COLORS["border"]}', # Using new 'border'
        'boxShadow': '0 2px 4px rgba(0,0,0,0.2)', # Slightly more prominent shadow for dark theme
        'marginBottom': '20px'
    }
}

UI_COMPONENTS = {
    'table_cell_right': {'textAlign': 'right'},
    'table_na_row': {'colSpan': 2},
    'font_default': {'fontFamily': 'Arial, sans-serif'},
    'default_container': {
        'backgroundColor': COLORS['background'], # Using new 'background' color
        'padding': '20px',
        'minHeight': '100vh'
    }
}