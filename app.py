import dash
import sys, os
# Ensure this path is correct for your module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from layout.core_layout import create_main_layout
from callbacks import register_all_callbacks

app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder='assets')
server = app.server

# Define Assets URLs directly in app.py where 'app' is available
ICON_UPLOAD_DEFAULT = app.get_asset_url('upload_file_csv_icon.png')
ICON_UPLOAD_SUCCESS = app.get_asset_url('upload_file_csv_icon_success.png')
ICON_UPLOAD_FAIL = app.get_asset_url('upload_file_csv_icon_fail.png')
MAIN_LOGO_PATH = app.get_asset_url('yosai_logo_name_black.png')

# Pass the asset URLs explicitly to create_main_layout
app.layout = create_main_layout(
    app_instance=app,
    main_logo_path=MAIN_LOGO_PATH,
    icon_upload_default=ICON_UPLOAD_DEFAULT # Also pass the default upload icon
)

# Register everything - already correct, just ensure it uses these passed URLs
register_all_callbacks(
    app,
    ICON_UPLOAD_DEFAULT,
    ICON_UPLOAD_SUCCESS,
    ICON_UPLOAD_FAIL,
    MAIN_LOGO_PATH
)

if __name__ == "__main__":
    app.run(debug=True)