def setup(app):
    app.add_config_value("show_solutions", False, "env")

    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

