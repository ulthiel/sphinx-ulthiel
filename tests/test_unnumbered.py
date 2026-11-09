"""Integration regressions for structural, inherited unnumbered headings.

Run with ``python -m unittest discover -s tests -v`` after installing the test
extra. The tests build small independent Sphinx projects in temporary directories.
"""

from contextlib import contextmanager
from importlib.util import find_spec
from io import StringIO
from pathlib import Path
import re
import tempfile
import unittest

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from docutils import nodes
from sphinx.environment.collectors.toctree import TocTreeCollector
from sphinx.testing.util import SphinxTestApp


SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'


def objects(suffix, kind):
    return f"""
:::{{figure}} tiny.svg
:name: fig-{suffix}

Figure {suffix}.
:::

:::{{prf:{kind}}}
:label: statement-{suffix}

Statement {suffix}.
:::
"""


CHAPTER = """(alpha)=
# Alpha

(alpha-intro)=
{.unnumbered}
## Introduction

Introductory prose.

(alpha-intro-child)=
### Nested introduction

This child inherits the unnumbered status.

(alpha-main)=
## Overview

""" + objects("before", "definition") + """
(alpha-aside)=
{.unnumbered}
### Overview

This title deliberately duplicates a numbered section title.

""" + objects("inside", "lemma") + """
(alpha-deep)=
#### Deep appendix

This descendant has no explicit class.

""" + objects("deep", "theorem") + """
(alpha-child)=
### Numbered child

""" + objects("after", "exercise") + """
(alpha-next)=
## Next

Later numbered sibling.
"""

REFERENCES = """# References

Unnumbered introduction: {secref}`alpha-intro`.

Inherited unnumbered introduction: {secref}`alpha-intro-child`.

Numbered section: {secref}`alpha-main`.

Duplicate-title unnumbered section: {secref}`alpha-aside`.

Inherited unnumbered descendant: {secref}`alpha-deep`.

Numbered child: {secref}`alpha-child`.

Following section: {secref}`alpha-next`.

Ordinary section reference: {ref}`alpha-aside`.

Custom section reference: {ref}`custom text <alpha-main>`.

Figure references: {numref}`fig-before`, {numref}`fig-inside`, {numref}`fig-deep`, {numref}`fig-after`.

Statement references: {prf:ref}`statement-before`, {prf:ref}`statement-inside`, {prf:ref}`statement-deep`, {prf:ref}`statement-after`.
"""


@unittest.skipUnless(
    BeautifulSoup is not None and find_spec("myst_parser") and find_spec("sphinx_proof"),
    "requires the MyST, beautifulsoup4, and sphinx-proof testing dependencies",
)
class UnnumberedIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ulthiel-test-")
        self.root = Path(self.temporary.name)
        self.src = self.root / "src"
        self.src.mkdir()
        self.addCleanup(self.temporary.cleanup)

    def write(self, files):
        for name, content in files.items():
            target = self.src / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf8")

    def prepare(self, chapter=CHAPTER, index=None, extensions=None, extra=""):
        extensions = extensions or ["myst_parser", "sphinx_ulthiel", "sphinx_proof"]
        config = f"""extensions = {extensions!r}
project = 'Unnumbered integration tests'
root_doc = 'index'
html_theme = 'alabaster'
html_sidebars = {{'**': ['localtoc.html']}}
source_suffix = {{'.rst': 'restructuredtext', '.md': 'markdown'}}
myst_enable_extensions = ['colon_fence', 'attrs_block']
numfig = True
numfig_secnum_depth = 2
numfig_format = {{'figure': 'Figure %s'}}
proof_shared_counter = True
""" + extra
        self.write({
            "conf.py": config,
            "index.rst": index or """Root
====

.. toctree::
   :numbered: 4

   chapter
   refs
""",
            "chapter.md": chapter,
            "refs.md": REFERENCES,
            "tiny.svg": SVG,
        })

    @contextmanager
    def app(self, freshenv=True, parallel=0):
        # Other supported extensions replace this class method globally too.
        # Restore it between projects so test order cannot select the numberer.
        original = TocTreeCollector.assign_section_numbers
        warning = StringIO()
        app = SphinxTestApp(
            srcdir=self.src,
            builddir=self.root / "build",
            freshenv=freshenv,
            warning=warning,
            warningiserror=True,
            keep_going=True,
            parallel=parallel,
        )
        try:
            app.build()
            self.assertEqual(warning.getvalue().strip(), "")
            yield app
        finally:
            app.cleanup()
            TocTreeCollector.assign_section_numbers = original

    def soup(self, app, docname):
        return BeautifulSoup((app.outdir / f"{docname}.html").read_text(), "html.parser")

    def heading(self, app, docname, label):
        soup = self.soup(app, docname)
        _, anchor, _ = app.env.domains["std"].data["labels"][label]
        target = soup.find(id=anchor)
        self.assertIsNotNone(target, label)
        if target.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return target
        return target.find(re.compile(r"^h[1-6]$")) or target.find_next(re.compile(r"^h[1-6]$"))

    def assert_heading(self, app, docname, label, number):
        heading = self.heading(app, docname, label)
        self.assertIsNotNone(heading, label)
        rendered = heading.select_one(".section-number")
        if number is None:
            self.assertIsNone(rendered, label)
        else:
            self.assertIsNotNone(rendered, label)
            self.assertEqual(rendered.get_text().strip().rstrip("."), number, label)

    def assert_reference(self, app, source, label, text):
        docname, anchor, _ = app.env.domains["std"].data["labels"][label]
        href = ("" if source == docname else f"{docname}.html") + "#" + anchor
        links = self.soup(app, source).find_all("a", href=href)
        self.assertIn(text, [a.get_text() for a in links], (label, href))

    def test_inheritance_toc_refs_and_ancestor_counters(self):
        self.prepare()
        with self.app() as app:
            for label, number in {
                "alpha": "1",
                "alpha-intro": None,
                "alpha-intro-child": None,
                "alpha-main": "1.1",
                "alpha-aside": None,
                "alpha-deep": None,
                "alpha-child": "1.1.1",
                "alpha-next": "1.2",
            }.items():
                self.assert_heading(app, "chapter", label, number)

            # These remain structural sections and real TOC entries, not rubrics.
            toc = app.env.tocs["chapter"]
            toc_links = list(toc.findall(nodes.reference))
            sidebar = self.soup(app, "chapter").select_one(".sphinxsidebar")
            sections = list(app.env.get_doctree("chapter").findall(nodes.section))
            for label in ["alpha-intro", "alpha-intro-child", "alpha-aside", "alpha-deep"]:
                _, anchor, _ = app.env.domains["std"].data["labels"][label]
                section = next(s for s in sections if anchor in s["ids"])
                matching = [r for r in toc_links if r.get("anchorname") == "#" + section["ids"][0]]
                self.assertEqual(len(matching), 1, label)
                key = matching[0]["anchorname"]
                self.assertIn(key, app.env.toc_secnumbers["chapter"], label)
                self.assertIsNone(app.env.toc_secnumbers["chapter"][key], label)
                self.assertIsNotNone(sidebar.find("a", href=key), label)

            for label, title in {
                "alpha-intro": "Introduction",
                "alpha-intro-child": "Nested introduction",
                "alpha-main": "Section 1.1",
                "alpha-aside": "Overview",
                "alpha-deep": "Deep appendix",
                "alpha-child": "Section 1.1.1",
                "alpha-next": "Section 1.2",
            }.items():
                self.assert_reference(app, "refs", label, title)
            self.assert_reference(app, "refs", "alpha-main", "custom text")

            for number, suffix, kind in [
                (1, "before", "Definition"),
                (2, "inside", "Lemma"),
                (3, "deep", "Theorem"),
                (4, "after", "Exercise"),
            ]:
                self.assertEqual(app.env.toc_fignumbers["chapter"]["figure"][f"fig-{suffix}"], (1, 1, number))
                self.assertEqual(app.env.toc_fignumbers["chapter"]["proof"][f"statement-{suffix}"], (1, 1, number))
                block = self.soup(app, "chapter").find(id=f"statement-{suffix}")
                self.assertTrue(block.select_one(".admonition-title").get_text().startswith(f"{kind} 1.1.{number}"))
                references = self.soup(app, "refs")
                figure_links = references.find_all("a", href=f"chapter.html#fig-{suffix}")
                self.assertIn(f"Figure 1.1.{number}", [a.get_text() for a in figure_links])
                proof_links = references.find_all("a", href=f"chapter.html#statement-{suffix}")
                self.assertIn(f"{kind} 1.1.{number}", [a.get_text() for a in proof_links])

    def test_unmarked_headings_keep_stock_numbering(self):
        self.prepare(chapter=CHAPTER.replace("{.unnumbered}\n", ""))
        with self.app() as app:
            for label, number in {
                "alpha-intro": "1.1",
                "alpha-intro-child": "1.1.1",
                "alpha-main": "1.2",
                "alpha-aside": "1.2.1",
                "alpha-deep": "1.2.1.1",
                "alpha-child": "1.2.2",
                "alpha-next": "1.3",
            }.items():
                self.assert_heading(app, "chapter", label, number)

    def test_multiple_numbered_toctrees_stock_and_multitoc(self):
        index = """Root
====

.. toctree::
   :numbered: 4

   chapter
   refs

.. toctree::
   :numbered: 4

   gamma
   delta
"""
        for order in [None, "before", "after"]:
            with self.subTest(multitoc_order=order):
                if order and find_spec("sphinx_multitoc_numbering") is None:
                    self.skipTest("requires sphinx-multitoc-numbering")
                extensions = ["myst_parser", "sphinx_ulthiel", "sphinx_proof"]
                if order == "after":
                    extensions.append("sphinx_multitoc_numbering")
                elif order == "before":
                    extensions.insert(1, "sphinx_multitoc_numbering")
                self.prepare(index=index, extensions=extensions)
                self.write({"gamma.md": """(gamma)=
# Gamma

{.unnumbered}
## Introduction

(gamma-descendant)=
### Inherited descendant

(gamma-first)=
## First numbered section
""", "delta.md": "(delta)=\n# Delta\n"})
                with self.app() as app:
                    prefix = "3" if order else "1"
                    self.assert_heading(app, "gamma", "gamma", prefix)
                    self.assert_heading(app, "gamma", "gamma-first", prefix + ".1")
                    self.assert_heading(app, "gamma", "gamma-descendant", None)
                    self.assert_heading(app, "delta", "delta", "4" if order else "2")
                    self.assert_heading(app, "chapter", "alpha-next", "1.2")

    @unittest.skipUnless(find_spec("sphinx_external_toc"), "requires sphinx-external-toc")
    def test_external_toc_keeps_numbered_documents_under_unnumbered_intro(self):
        extensions = ["myst_parser", "sphinx_external_toc", "sphinx_ulthiel", "sphinx_proof"]
        self.prepare(extensions=extensions, extra="external_toc_path = '_toc.yml'\n")
        (self.src / "index.rst").unlink()
        # All available documents are included, so warning-free builds stay strict.
        self.write({
            "index.md": "# Book\n",
            "lecture.md": """(lecture)=
# Lecture notes

(lecture-intro)=
{.unnumbered}
## Introduction

(lecture-motivation)=
### Motivation

(lecture-guide)=
{.unnumbered}
## Course guide

Course prose.
""",
            "_toc.yml": """format: jb-book
root: index
options:
  numbered: 4
chapters:
  - file: lecture
    sections:
      - file: chapter
      - file: refs
""",
        })
        with self.app() as app:
            self.assert_heading(app, "lecture", "lecture", "1")
            self.assert_heading(app, "lecture", "lecture-intro", None)
            self.assert_heading(app, "lecture", "lecture-motivation", None)
            self.assert_heading(app, "lecture", "lecture-guide", None)
            self.assert_heading(app, "chapter", "alpha", "1.1")
            self.assert_heading(app, "chapter", "alpha-main", "1.1.1")
            self.assert_heading(app, "chapter", "alpha-next", "1.1.2")
            self.assert_reference(app, "refs", "alpha-aside", "Overview")

    @unittest.skipUnless(find_spec("sphinx_external_toc"), "requires sphinx-external-toc")
    def test_external_toc_roman_style_preserves_unnumbered_sections(self):
        extensions = ["myst_parser", "sphinx_external_toc", "sphinx_ulthiel", "sphinx_proof"]
        self.prepare(extensions=extensions, extra="external_toc_path = '_toc.yml'\n")
        (self.src / "index.rst").unlink()
        self.write({
            "index.md": "# Book\n",
            "_toc.yml": """format: jb-book
root: index
options:
  numbered: 4
  style: [romanupper, numerical]
chapters:
  - file: chapter
  - file: refs
""",
        })
        with self.app() as app:
            self.assert_heading(app, "chapter", "alpha", "I")
            self.assert_heading(app, "chapter", "alpha-main", "I.1")
            self.assert_heading(app, "chapter", "alpha-aside", None)
            self.assert_heading(app, "chapter", "alpha-deep", None)
            self.assert_heading(app, "chapter", "alpha-child", "I.1.1")
            self.assert_heading(app, "chapter", "alpha-next", "I.2")
            self.assert_reference(app, "refs", "alpha-main", "Section I.1")
            self.assert_reference(app, "refs", "alpha-aside", "Overview")
            self.assertEqual(app.env.toc_fignumbers["chapter"]["figure"]["fig-inside"], ("I", 1, 2))
            self.assertEqual(app.env.toc_fignumbers["chapter"]["proof"]["statement-inside"], ("I", 1, 2))

    def test_incremental_secref_only_references_are_updated(self):
        self.prepare()
        self.write({"refs.md": "# References\n\n{secref}`alpha-main`\n"})
        with self.app() as app:
            self.assert_reference(app, "refs", "alpha-main", "Section 1.1")
        source = self.src / "chapter.md"
        source.write_text(source.read_text().replace("{.unnumbered}\n", "", 1))
        with self.app(freshenv=False) as app:
            self.assert_heading(app, "chapter", "alpha-main", "1.2")
            self.assert_reference(app, "refs", "alpha-main", "Section 1.2")

    def test_incremental_numref_only_references_are_updated(self):
        self.prepare()
        self.write({"refs.md": "# References\n\n{numref}`fig-before`\n"})
        with self.app() as app:
            self.assert_reference(app, "refs", "fig-before", "Figure 1.1.1")
        source = self.src / "chapter.md"
        source.write_text(source.read_text().replace("{.unnumbered}\n", "", 1))
        with self.app(freshenv=False) as app:
            self.assertEqual(app.env.toc_fignumbers["chapter"]["figure"]["fig-before"], (1, 2, 1))
            self.assert_reference(app, "refs", "fig-before", "Figure 1.2.1")

    def test_incremental_add_and_remove_final_marker(self):
        numbered = "(alpha)=\n# Alpha\n\n(alpha-main)=\n## Overview\n"
        unnumbered = numbered.replace("## Overview", "{.unnumbered}\n## Overview")
        self.prepare(chapter=numbered)
        self.write({"refs.md": "# References\n\n{secref}`alpha-main`\n"})
        with self.app() as app:
            self.assert_reference(app, "refs", "alpha-main", "Section 1.1")
        self.write({"chapter.md": unnumbered})
        with self.app(freshenv=False) as app:
            self.assert_heading(app, "chapter", "alpha-main", None)
            self.assert_reference(app, "refs", "alpha-main", "Overview")
        self.write({"chapter.md": numbered})
        with self.app(freshenv=False) as app:
            self.assert_heading(app, "chapter", "alpha-main", "1.1")
            self.assert_reference(app, "refs", "alpha-main", "Section 1.1")

    def test_noop_build_does_not_rewrite_documents(self):
        self.prepare()
        with self.app() as app:
            files = [app.outdir / "chapter.html", app.outdir / "refs.html"]
            before = [path.stat().st_mtime_ns for path in files]
        with self.app(freshenv=False) as app:
            self.assertEqual([path.stat().st_mtime_ns for path in files], before)
            self.assert_reference(app, "refs", "alpha-aside", "Overview")

    def test_parallel_read_merges_section_metadata(self):
        chapter = """(alpha)=
# Alpha

(alpha-intro)=
{.unnumbered}
## Introduction

(alpha-intro-child)=
### Inherited child

(alpha-main)=
## Main section
"""
        self.prepare(chapter=chapter, extensions=["myst_parser", "sphinx_ulthiel"])
        self.write({"refs.md": "# References\n\n{secref}`alpha-intro-child`, {secref}`alpha-main`\n"})
        # Sphinx only parallelizes reading when more than five files change.
        index = self.src / "index.rst"
        index.write_text(index.read_text() + "".join(f"   extra{i}\n" for i in range(4)))
        for i in range(4):
            self.write({f"extra{i}.md": f"""# Extra {i}

(extra{i}-intro)=
{{.unnumbered}}
## Introduction

(extra{i}-main)=
## Main section
"""})
        with self.app(parallel=2) as app:
            self.assert_heading(app, "extra3", "extra3-intro", None)
            self.assert_heading(app, "extra3", "extra3-main", "6.1")
            self.assert_heading(app, "chapter", "alpha-intro-child", None)
            self.assert_heading(app, "chapter", "alpha-main", "1.1")
            self.assert_reference(app, "refs", "alpha-intro-child", "Inherited child")
            self.assert_reference(app, "refs", "alpha-main", "Section 1.1")

    def test_parallel_write_preserves_proof_counters(self):
        self.prepare()
        with self.app(parallel=2) as app:
            self.assert_heading(app, "chapter", "alpha-aside", None)
            self.assert_heading(app, "chapter", "alpha-next", "1.2")
            self.assert_reference(app, "refs", "alpha-main", "Section 1.1")
            self.assert_reference(app, "refs", "alpha-aside", "Overview")
            self.assertEqual(app.env.toc_fignumbers["chapter"]["proof"]["statement-deep"], (1, 1, 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
