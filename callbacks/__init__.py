from .upload_callbacks import register_upload_callbacks
from .mapping_callbacks import register_mapping_callbacks
from .graph_callbacks import register_graph_callbacks

def register_all_callbacks(app, icon_upload_default, icon_upload_success, icon_upload_fail):
    register_upload_callbacks(app, icon_upload_default, icon_upload_success, icon_upload_fail)
    register_mapping_callbacks(app)
    register_graph_callbacks(app)

