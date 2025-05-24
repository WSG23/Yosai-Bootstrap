# File: app.py
from server import create_app
from layout.layout import build_layout
import callbacks.upload_handlers
import callbacks.mapping_flow
import callbacks.graph_generation

app = create_app()
app.layout = build_layout(app)

if __name__ == "__main__":
    app.run(debug=True)
