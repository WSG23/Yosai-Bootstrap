import dash
import sys, os
import dash_bootstrap_components as dbc # ✅ NEW IMPORT



sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from layout.core_layout import create_main_layout
from callbacks import register_all_callbacks

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder='assets',
    # ✅ CHANGE THIS LINE TO A DARK BOOTSTRAP THEME
    external_stylesheets=[dbc.themes.DARKLY] # Or dbc.themes.CYBORG, dbc.themes.SLATE, dbc.themes.SUPERHERO
)

server = app.server

# Assets
ICON_UPLOAD_DEFAULT = app.get_asset_url('upload_file_csv_icon.png') # Using corrected filenames
ICON_UPLOAD_SUCCESS = app.get_asset_url('upload_file_csv_icon_success.png')
ICON_UPLOAD_FAIL = app.get_asset_url('upload_file_csv_icon_fail.png')
MAIN_LOGO_PATH = app.get_asset_url('yosai_logo_name_white.png')

app.layout = create_main_layout(
    app_instance=app,
    main_logo_path=MAIN_LOGO_PATH,
    icon_upload_default=ICON_UPLOAD_DEFAULT
)

register_all_callbacks(
    app,
    ICON_UPLOAD_DEFAULT,
    ICON_UPLOAD_SUCCESS,
    ICON_UPLOAD_FAIL,
    MAIN_LOGO_PATH
)

if __name__ == "__main__":
    app.run(debug=True)