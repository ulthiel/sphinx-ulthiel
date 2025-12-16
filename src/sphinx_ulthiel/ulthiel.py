from .keyterm import setup_keyterm
from .highlight import setup_highlight

def setup(app):
    app.add_config_value("show_solutions", False, "env")

    setup_keyterm(app)
    setup_highlight(app)

    return {
        "version": "0.2.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

