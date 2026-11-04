from .keyterm import setup_keyterm
from .highlight import setup_highlight
from .secref import setup_secref
from .unnumbered import setup_unnumbered

def setup(app):
    app.add_config_value("show_solutions", False, "env")
    app.add_config_value("show_private", False, "env")
    app.add_config_value("show_teacher", False, "env")
    app.add_config_value("show_course_scope", False, "env")

    setup_keyterm(app)
    setup_highlight(app)
    setup_secref(app)
    setup_unnumbered(app)

    return {
        "version": "0.3.0",
        "env_version": 1,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

