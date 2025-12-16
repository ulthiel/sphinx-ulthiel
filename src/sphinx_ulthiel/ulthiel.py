from .keyterm import setup_keyterm

def setup(app):
    app.add_config_value("show_solutions", False, "env")

    setup_keyterm(app)

    return {
        "version": "0.2.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

