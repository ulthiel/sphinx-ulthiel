from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import roles
from sphinx import addnodes  # <-- this is the important change


def _split_display_and_indices(text: str) -> tuple[str, list[str] | None]:
    """
    Syntax supported:

      :keyterm:`morphism`
        -> display="morphism", no index

      :keyterm:`morphism <>`
        -> display="morphism", explicitly no index

      :keyterm:`morphism <affine algebraic variety; morphism>`
        -> one index entry

      :keyterm:`morphism <affine algebraic variety; morphism | morphism; affine algebraic varieties>`
        -> multiple index entries
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

    # Inline node for styling (HTML class "keyterm")
    term_node = nodes.inline(display, display, classes=["keyterm"])

    if not indices:
        return [term_node], []

    # One Sphinx index node per entry
    index_nodes = [
        addnodes.index(entries=[("single", entry, entry, "", None)])
        for entry in indices
    ]

    return index_nodes + [term_node], []


def setup_keyterm(app) -> None:
    roles.register_local_role("keyterm", keyterm_role)
