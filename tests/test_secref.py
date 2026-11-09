"""Rendered integration tests for numbered and localized section references."""

from contextlib import contextmanager
from importlib.util import find_spec
from io import StringIO
from pathlib import Path
import tempfile
import unittest

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from sphinx.environment.collectors.toctree import TocTreeCollector
from sphinx.testing.util import SphinxTestApp


GEOMETRY = """(geometry)=
# Geometry

(overview)=
## Overview

:::{figure} tiny.svg
:name: tiny-figure

A small figure.
:::

(coordinates)=
### Coordinates

(deep)=
#### Beyond the numbering depth

(aside)=
{.unnumbered}
## Overview

(aside-child)=
### Further details

(next)=
## Next section

Same-document references: {secref}`geometry`, {secref}`overview`,
{secref}`coordinates`, {secref}`deep`, {secref}`aside`, {secref}`aside-child`.

Plain reference: {ref}`overview`.

Custom reference: {ref}`custom caption <overview>`.

Figure reference: {numref}`tiny-figure`.
"""

REFERENCES = """# References

Cross-document references: {secref}`geometry`, {secref}`overview`,
{secref}`coordinates`, {secref}`deep`, {secref}`aside`, {secref}`aside-child`.
"""


@unittest.skipUnless(
    BeautifulSoup is not None and find_spec("myst_parser"),
    "requires the MyST and beautifulsoup4 testing dependencies",
)
class SectionReferenceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ulthiel-secref-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.src = self.root / "src"
        self.src.mkdir()

    def prepare(self, documents=None, language="en"):
        documents = documents or {"geometry": GEOMETRY, "refs": REFERENCES}
        config = f"""extensions = ['myst_parser', 'sphinx_ulthiel']
project = 'Section reference integration tests'
root_doc = 'index'
html_theme = 'alabaster'
source_suffix = {{'.rst': 'restructuredtext', '.md': 'markdown'}}
myst_enable_extensions = ['colon_fence', 'attrs_block']
language = {language!r}
numfig = True
numfig_secnum_depth = 2
numfig_format = {{'figure': 'Figure %s'}}
"""
        (self.src / "conf.py").write_text(config, encoding="utf8")
        index = "Root\n====\n\n.. toctree::\n   :numbered: 3\n\n"
        index += "".join(f"   {name}\n" for name in documents)
        (self.src / "index.rst").write_text(index, encoding="utf8")
        for name, content in documents.items():
            (self.src / f"{name}.md").write_text(content, encoding="utf8")
        (self.src / "tiny.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>',
            encoding="utf8",
        )

    @contextmanager
    def app(self):
        # The numbering extension patches this class method globally.
        original = TocTreeCollector.assign_section_numbers
        warning = StringIO()
        app = SphinxTestApp(
            srcdir=self.src,
            builddir=self.root / "build",
            freshenv=True,
            warning=warning,
            warningiserror=True,
            keep_going=True,
        )
        try:
            app.build()
            self.assertEqual(warning.getvalue().strip(), "")
            yield app
        finally:
            app.cleanup()
            TocTreeCollector.assign_section_numbers = original

    def links(self, app, source, label):
        target, anchor, _ = app.env.domains["std"].data["labels"][label]
        href = ("" if source == target else f"{target}.html") + "#" + anchor
        soup = BeautifulSoup(
            (app.outdir / f"{source}.html").read_text(encoding="utf8"),
            "html.parser",
        )
        # Scope assertions to prose references, excluding heading permalinks
        # and the theme's duplicate links in its local contents/sidebar.
        return [
            link.get_text()
            for link in soup.select("div.body p a.reference.internal")
            if link.get("href") == href
        ]

    def test_numbered_same_and_cross_document_references(self):
        self.prepare()
        with self.app() as app:
            for source in ["geometry", "refs"]:
                for label, expected in {
                    "geometry": "Section 1",
                    "overview": "Section 1.1",
                    "coordinates": "Section 1.1.1",
                }.items():
                    with self.subTest(source=source, target=label):
                        self.assertIn(expected, self.links(app, source, label))
            # The change is specific to secref; ordinary ref and numref retain
            # their title/custom text and figure-number rendering.
            self.assertCountEqual(
                self.links(app, "geometry", "overview"),
                ["Section 1.1", "Overview", "custom caption"],
            )
            self.assertIn(
                "Figure 1.1.1", self.links(app, "geometry", "tiny-figure")
            )

    def test_unnumbered_and_depth_cutoff_never_inherit_a_parent_number(self):
        self.prepare()
        with self.app() as app:
            for source in ["geometry", "refs"]:
                for label, expected in {
                    "deep": "Beyond the numbering depth",
                    "aside": "Overview",
                    "aside-child": "Further details",
                }.items():
                    with self.subTest(source=source, target=label):
                        self.assertEqual(self.links(app, source, label), [expected])
            # The actual parent remains numbered; the duplicate title of the
            # explicit unnumbered heading must not borrow its sibling's number.
            self.assertEqual(
                self.links(app, "refs", "coordinates"), ["Section 1.1.1"]
            )
            self.assertEqual(
                self.links(app, "refs", "overview"), ["Section 1.1"]
            )

    def test_language_comes_from_the_referencing_document(self):
        self.prepare({
            "english": """(english)=
# English document

(english-section)=
## English section

{secref}`english-section`; {secref}`german-section`.
""",
            "german": """<!-- LTeX: language=de-DE -->

(german)=
# Deutsches Dokument

(german-section)=
## Deutscher Abschnitt

{secref}`german-section`; {secref}`english-section`.
""",
        })
        with self.app() as app:
            for source, prefix in [("english", "Section"), ("german", "Abschnitt")]:
                for target, number in [
                    ("english-section", "1.1"),
                    ("german-section", "2.1"),
                ]:
                    with self.subTest(source=source, target=target):
                        self.assertEqual(
                            self.links(app, source, target), [f"{prefix} {number}"]
                        )

    def test_german_sphinx_language_is_the_fallback(self):
        # Neither document has an LTeX language marker.
        self.prepare(language="de")
        with self.app() as app:
            for source in ["geometry", "refs"]:
                self.assertIn(
                    "Abschnitt 1.1", self.links(app, source, "overview")
                )
                self.assertEqual(
                    self.links(app, source, "deep"), ["Beyond the numbering depth"]
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
