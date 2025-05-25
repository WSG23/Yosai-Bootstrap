from .upload_callbacks import register_upload_callbacks
from .mapping_callbacks import register_mapping_callbacks
from .graph_callbacks import register_graph_callbacks

def register_all_callbacks(app, icon_default, icon_success, icon_fail, logo_path):
    # Register each callback group
    register_upload_callbacks(app, icon_default, icon_success, icon_fail)
    register_mapping_callbacks(app)
    register_graph_callbacks(app)
