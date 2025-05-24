# File: server.py
import dash


def create_app():
    """
    Create and configure the Dash app.
    """
    app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder="assets")
    return app
