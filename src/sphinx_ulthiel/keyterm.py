from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import roles
from sphinx import addnodes
from sphinx.util.nodes import make_id


def _split_display_and_indices(text: str) -> tuple[str, list[str] | None]:
    """
    Supported syntax:

      :keyterm:`morphism`
        -> visible only, no index, no anchor

      :keyterm:`morphism <>`
        -> visible only, explicit no index

      :keyterm:`morphism <matroid>`
        -> visible + index entry + anchor

      :keyterm:`morphism <matroid; morphism | morphism; matroid>`
        -> visible + multiple index entries + anchor
    """
    t = text.strip()

    if "<" in t and t.endswith(">"):
        display, idx = t.rsplit("<", 1)
        display = display.strip()
        idx = idx[:-1].strip()  # drop trailing '>'

        if idx == "":
            return display, None

        entries = [e.strip() for e in idx.split("|") if e.strip()]
        return display, entries or None

    return t, None


def keyterm_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner,
    options=None,
    content=None,
):
    display, indices = _split_display_and_indices(text)

    # Visible inline node
    term_node = nodes.inline(display, display, classes=["keyterm"])

    # No indexing → no anchor
    if not indices:
        return [term_node], []

    # Create a namespaced, stable anchor for indexing
    anchor_id = make_id(f"index-{display}")
    target = nodes.target("", "", ids=[anchor_id])

    # Create index entries pointing to the anchor
    index_nodes = [
        addnodes.index(
            entries=[("single", entry, anchor_id, "", None)]
        )
        for entry in indices
    ]

    # Order matters: target → index → visible text
    return [target, *index_nodes, term_node], []


def setup_keyterm(app) -> None:
    roles.register_local_role("keyterm", keyterm_role)
