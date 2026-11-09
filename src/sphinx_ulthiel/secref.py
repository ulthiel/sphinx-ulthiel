from __future__ import annotations

import re
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

    # Resolve explicit labels by section identity before comparing titles.
    # Different sections may have identical titles.
    toc = env.tocs.get(docname)
    if toc is None:
        return None

    for ref in toc.findall(nodes.reference):
        if labelid.lstrip("#") in ref.get("ulthiel_section_ids", []):
            return secnumbers.get(ref.get("anchorname", ""))

    # Compatibility with doctrees collected before section IDs were recorded.
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


def section_prefix(app: Sphinx, doctree: nodes.document) -> str:
    """Use the referring document's language, falling back to Sphinx's language."""
    language = app.config.language or "en"
    marker = re.compile(
        r"\s*LTeX:\s*language\s*=\s*([a-z]+(?:[-_][a-z0-9]+)*)\s*",
        re.IGNORECASE,
    )
    for node in doctree.findall(
        lambda item: isinstance(item, (nodes.comment, nodes.raw))
    ):
        comments = (
            [node.astext()]
            if isinstance(node, nodes.comment)
            else re.findall(r"<!--(.*?)-->", node.astext(), re.DOTALL)
        )
        for comment in comments:
            match = marker.fullmatch(comment)
            if match:
                language = match[1]
                break
        else:
            continue
        break
    return "Abschnitt" if re.split(r"[-_]", language.lower())[0] == "de" else "Section"


def resolve_secref(app: Sphinx, doctree: nodes.document, fromdocname: str) -> None:
    env = app.builder.env
    labels = env.domains["std"].data["labels"]
    prefix = section_prefix(app, doctree)

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
            reftext = prefix + " " + ".".join(str(i) for i in secnum)
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
