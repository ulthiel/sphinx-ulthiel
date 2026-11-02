# sphinx-ulthiel

My personal extra struff for the Sphinx documentation engine.

* New config variable `show_solutions` (default false) to be used with ifconfig to toggle showing solutions for exercises or not.
* New config variable `show_private` (default false) to be used with ifconfig to toggle showing private sections or not.
* New role {keyterm} for typesetting terms (class keyterm) and automatically adding them to the index.
* New role {highlight} for highlighting text (class highlight-text).

## Unnumbered sections in the table of contents

Add the `unnumbered` class to a section to keep its heading and TOC entry
without assigning or consuming a section number in HTML output (including
browser printing). Its subsections are also
unnumbered; later numbered siblings continue without a gap. Document links,
section labels, and the hierarchy of the displayed TOC are preserved.
Figures and other numbered objects inherit the nearest numbered ancestor.
Separate documents included through a `toctree` retain their own numbering.

With MyST Markdown, enable `attrs_block` in `myst_enable_extensions` and write:

```md
(course-guide)=
{.unnumbered}
## Course guide

### Reading suggestions
```

In reStructuredText, use `.. rst-class:: unnumbered` immediately before the
section heading. The extension works with Sphinx's standard numbering and
with `sphinx-multitoc-numbering`, including Jupyter Book v1's external TOCs.

Use `{secref}` with a section label to link to its number and title. For an
unnumbered section this role displays only the linked title. Use rubrics for
non-structural headings that should stay out of the TOC.

## Development tests

Install the test dependencies and run the integration tests from this checkout:

```sh
python -m pip install -e '.[test]'
python -m unittest discover -s tests -v
```

The tests build small Sphinx projects and check rendered headings, TOCs,
references, figure and proof counters, and incremental rebuilds. The test
extra uses the `ulthiel/sphinx-proof` fork for its shared statement counter.
