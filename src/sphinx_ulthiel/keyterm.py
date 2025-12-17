from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import roles
from sphinx import addnodes


def _split_display_and_indices(text: str) -> tuple[str, list[str] | None]:
    t = text.strip()

    if "<" in t and t.endswith(">"):
        display, idx = t.rsplit("<", 1)
        display = display.strip()
        idx = idx[:-1].strip()

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

    term_node = nodes.inline(display, display, classes=["keyterm"])

    # No indexing → no anchor
    if not indices:
        return [term_node], []

    # Deterministic, namespaced anchor
    anchor_id = nodes.make_id(f"index-{display}")
    target = nodes.target("", "", ids=[anchor_id])

    index_nodes = [
        addnodes.index(
            entries=[("single", entry, anchor_id, "", None)]
        )
        for entry in indices
    ]

    return [target, *index_nodes, term_node], []


def setup_keyterm(app) -> None:
    roles.register_local_role("keyterm", keyterm_role)
