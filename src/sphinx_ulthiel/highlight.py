from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import roles


def highlight_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner,
    options=None,
    content=None,
):
    """
    :highlight:`arbitrary inline text`

    Semantic emphasis only.
    No indexing. Styling via CSS (.highlight).
    """
    node = nodes.inline(text, text, classes=["highlight"])
    return [node], []


def setup_highlight(app) -> None:
    roles.register_local_role("highlight", highlight_role)
