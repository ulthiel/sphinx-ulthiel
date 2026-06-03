from __future__ import annotations

from typing import Any

from docutils import nodes
from docutils.parsers.rst import roles
from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.nodes import make_refnode


logger = logging.getLogger(__name__)


class secref_node(nodes.Inline, nodes.Element):
    pass


def secref_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: dict[str, Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    node = secref_node(rawtext)
    node["reftarget"] = text.strip()
    return [node], []


def find_secnum(env: Any, docname: str, labelid: str, sectname: str):
    secnumbers = env.toc_secnumbers.get(docname, {})

    # First try the obvious keys.
    candidates = [
        labelid,
        labelid.lstrip("#"),
        "#" + labelid.lstrip("#"),
    ]

    for candidate in candidates:
        if candidate in secnumbers:
            return secnumbers[candidate]

    # MyST explicit labels may point to a target before the section,
    # while toc_secnumbers uses the actual generated section id.
    toc = env.tocs.get(docname)
    if toc is None:
        return None

    for ref in toc.findall(nodes.reference):
        if ref.astext() != sectname:
            continue

        anchor = ref.get("anchorname", "")
        refid = anchor.lstrip("#")

        for candidate in [refid, "#" + refid]:
            if candidate in secnumbers:
                return secnumbers[candidate]

        if "secnumber" in ref:
            return ref["secnumber"]

    return None


def resolve_secref(app: Sphinx, doctree: nodes.document, fromdocname: str) -> None:
    env = app.builder.env
    labels = env.domains["std"].data["labels"]

    for node in doctree.findall(secref_node):
        target = node["reftarget"]

        if target not in labels:
            logger.warning(
                "unknown secref target: %s",
                target,
                location=node,
            )
            node.replace_self(nodes.Text(f"??{target}??"))
            continue

        docname, labelid, sectname = labels[target]

        secnum = find_secnum(env, docname, labelid, sectname)

        if secnum:
            reftext = ".".join(str(i) for i in secnum) + " " + sectname
        else:
            reftext = sectname

        refnode = make_refnode(
            app.builder,
            fromdocname,
            docname,
            labelid,
            nodes.Text(reftext),
            sectname,
        )
        node.replace_self(refnode)


def setup_secref(app: Sphinx) -> None:
    app.add_node(secref_node)
    roles.register_local_role("secref", secref_role)
    app.connect("doctree-resolved", resolve_secref)