"""Keep unnumbered sections in the TOC without consuming section numbers."""

from __future__ import annotations

from copy import deepcopy
from functools import wraps

from docutils import nodes
from sphinx import addnodes
from sphinx.environment.collectors.toctree import TocTreeCollector


SECTION_IDS = "ulthiel_section_ids"
UNNUMBERED = "ulthiel_unnumbered"


def collect_sections(app, doctree):
    """Annotate the existing TOC, which already has purge/parallel-merge support."""
    sections = {}

    def walk(node, unnumbered=False):
        if isinstance(node, nodes.section):
            unnumbered = unnumbered or "unnumbered" in node["classes"]
            # Proof directives may contain synthetic sections without a title.
            if node.children and isinstance(node[0], nodes.title):
                for section_id in node["ids"]:
                    sections[section_id] = (list(node["ids"]), unnumbered)
        for child in node.children:
            if isinstance(child, nodes.Element):
                walk(child, unnumbered)

    walk(doctree)
    toc = app.env.tocs.get(app.env.docname)
    if toc is None:
        return
    first_section = next(iter(sections.values()), None)
    for ref in toc.findall(nodes.reference):
        anchor = ref.get("anchorname", "")
        section = sections.get(anchor.lstrip("#")) if anchor else first_section
        if section is not None:
            ref[SECTION_IDS], ref[UNNUMBERED] = section


def numbering_toc(toc):
    """Prune unnumbered local subtrees from a copy used only for numbering."""
    toc = toc.deepcopy()

    def prune(node):
        for child in list(node.children):
            if isinstance(child, nodes.list_item):
                paragraph = next(
                    (c for c in child if isinstance(c, addnodes.compact_paragraph)),
                    None,
                )
                if paragraph is not None and paragraph[0].get(UNNUMBERED):
                    # A toctree points to separate documents. Keep those numbered
                    # under the nearest numbered ancestor, even if their local
                    # introductory section is unnumbered.
                    nested = [n.deepcopy() for n in child.findall(addnodes.toctree)]
                    child.replace_self(nested)
                    continue
            if isinstance(child, nodes.Element):
                prune(child)

    prune(toc)
    return toc


def install_numbering(app):
    """Wrap the final numberer, including sphinx-multitoc-numbering's override."""
    original = TocTreeCollector.assign_section_numbers
    if getattr(original, "ulthiel_unnumbered", False):
        return

    @wraps(original)
    def assign_section_numbers(collector, env):
        tocs = env.tocs
        marked = {
            docname
            for docname, toc in tocs.items()
            if any(ref.get(UNNUMBERED) for ref in toc.findall(nodes.reference))
        }
        if not marked:
            return original(collector, env)

        old_numbers = env.toc_secnumbers
        env.tocs = {
            name: numbering_toc(toc) if name in marked else toc
            for name, toc in tocs.items()
        }
        try:
            original(collector, env)
        finally:
            env.tocs = tocs

        for docname in marked:
            numbers = env.toc_secnumbers.get(docname)
            for ref in tocs[docname].findall(nodes.reference):
                anchor = ref.get("anchorname", "")
                if ref.get(UNNUMBERED) and numbers is not None:
                    # An absent key falls back to the chapter number in HTML.
                    numbers[anchor] = None
                number = numbers.get(anchor) if numbers is not None else None
                # external-toc's style collector expects this attribute even
                # on unnumbered references, and mutates numbered values in place.
                ref["secnumber"] = list(number) if number else None
                if not anchor and ref.get(UNNUMBERED):
                    env.titles[docname]["secnumber"] = None

        # Compare the final maps, including explicit None entries. Comparing
        # the temporary pruned maps would rewrite these pages on every build.
        return [
            name
            for name in old_numbers.keys() | env.toc_secnumbers.keys()
            if old_numbers.get(name) != env.toc_secnumbers.get(name)
        ]

    assign_section_numbers.ulthiel_unnumbered = True
    TocTreeCollector.assign_section_numbers = assign_section_numbers


def update_section_references(app, env):
    """Rewrite incoming references after numbering changes, including removals."""
    from .secref import secref_node

    previous = getattr(env, "ulthiel_previous_section_numbers", {})
    current = env.toc_secnumbers
    changed = {
        name
        for name in previous.keys() | current.keys()
        if previous.get(name) != current.get(name)
    }
    env.ulthiel_previous_section_numbers = deepcopy(current)
    if not changed:
        return []

    std = env.domains["std"]
    labels = std.data["labels"]
    anonlabels = std.data["anonlabels"]
    rewrite = []
    for docname in env.found_docs:
        doctree = env.get_doctree(docname)
        for node in doctree.findall(
            lambda n: isinstance(n, secref_node)
            or (
                isinstance(n, addnodes.pending_xref)
                and n.get("refdomain") == "std"
                and n.get("reftype") == "numref"
            )
        ):
            target = node["reftarget"]
            label = labels.get(target) or anonlabels.get(target)
            if label is None or label[0] in changed:
                rewrite.append(docname)
                break
    return rewrite


def setup_unnumbered(app):
    # Run after the normal TOC collector and after other extensions have
    # installed their numbering implementation, regardless of extension order.
    app.connect("doctree-read", collect_sections, priority=800)
    app.connect("builder-inited", install_numbering, priority=800)
    app.connect("env-get-updated", update_section_references, priority=800)
