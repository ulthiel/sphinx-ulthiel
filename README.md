# sphinx-ulthiel

My personal extra struff for the Sphinx documentation engine.

* New config variable `show_solutions` (default false) to be used with ifconfig to toggle showing solutions for exercises or not.
* New config variable `show_private` (default false) to be used with ifconfig to toggle showing private sections or not.
* New config variable `show_teacher` (default false) to be used with ifconfig to show teaching notes in instructor builds.
* New config variable `show_course_scope` (default false) to be used with ifconfig to mark the material assigned in a course.
* New role {keyterm} for typesetting terms (class keyterm) and automatically adding them to the index.
* New role {highlight} for highlighting text (class highlight-text).

## Course scope

Enable `show_course_scope` in student and instructor builds to show brief
annotations identifying supplementary sections, optional proofs, and additional
exercise parts. Leave it false for a reading version without course annotations.
The flag does not hide any mathematical content.

With MyST Markdown and `sphinx.ext.ifconfig`, write:

```md
::::{ifconfig} show_course_scope
:::{admonition} Further study
This section and its subsections are supplementary reading.
:::
::::
```

Place each annotation at the highest heading to which it applies. For a mixed
section, identify only the optional passage or proof. Use `show_teacher`
separately if an instructor also needs private classroom instructions.

## Teaching notes

Set `show_teacher = True` in instructor builds to include comments about lecture
scope, omitted proofs, or classroom demonstrations. Leave it false in student
builds. The flag is independent of `show_solutions` and `show_private`.

With MyST Markdown and `sphinx.ext.ifconfig`, write:

```md
::::{ifconfig} show_teacher
:::{admonition} Teaching note
Skip this section and its subsections in the lecture.
:::
::::
```

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

Use `{secref}` with a section label to render a numbered target as
`Section 1.2.3`, without its title. An unnumbered target displays only its linked
title, including headings below the configured numbering depth. The title remains
available as a tooltip. References use the language of the referring document:
`Abschnitt 1.2.3` for German, otherwise `Section 1.2.3`. The document's LTeX
language comment (for example `<!-- LTeX: language=de-DE -->`) takes precedence
over Sphinx's `language` setting. Use rubrics for non-structural headings that
should stay out of the TOC.

## Development tests

Install the test dependencies and run the integration tests from this checkout:

```sh
python -m pip install -e '.[test]'
python -m unittest discover -s tests -v
```

The tests build small Sphinx projects and check rendered headings, TOCs,
references, figure and proof counters, and incremental rebuilds. The test
extra uses the `ulthiel/sphinx-proof` fork for its shared statement counter.

Assisted-by: Codex (gpt-6.1-sol) — updated section-reference formatting and regression tests.
