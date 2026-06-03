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

        secnum = env.toc_secnumbers.get(docname, {}).get(labelid)

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