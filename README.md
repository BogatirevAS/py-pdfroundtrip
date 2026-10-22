# Pdfroundtrip

**Structured PDF extraction and reconstruction.**

Extract text, tables, textboxes and chapters from a PDF into a portable dict/JSON,
edit it as ordinary Python data, then write it back into a new PDF — with **your**
structure, not the original layout.

Built on top of [PyMuPDF](https://pymupdf.io/), [pymupdf4llm](https://pypi.org/project/pymupdf4llm/)
and [pymupdf-layout](https://pypi.org/project/pymupdf-layout/).

> **Status:** Beta. Basic extraction and writing are covered by smoke tests;
> the API may still change between minor versions.
> PyMuPDF 2.0 support is planned for the next release — the current version targets PyMuPDF `1.28.x`.
-----

## Table of Contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Examples](#examples)
- [License](#license)
- [Third-party components and notices](#third-party-components-and-notices)

## About

`PdfExtractor` was developed to improve text extraction from PDF documents by organizing content into logical units,
such as textboxes, tables, and chapters. It achieves more accurate identification of table cells — surpassing popular
solutions like `PyMuPDF` and `pdfplumber` — by analyzing the graphical elements of the tables. The output is provided
in a convenient, flexible format suitable for analysis and further modification.
`PdfWriter` was developed to facilitate the creation of documents from this format; it features element-specific "add"
methods and highly configurable parameters. Key advantages include the automatic calculation of dimensions for element
rendering and page breaks, as well as enhanced rendering of textboxes, which supports the use of multiple styles
within a single textbox.

## Features

- **Semantic grouping** — text is grouped into textboxes, tables (with header detection)
  and chapters, not just raw strings.
- **Table reconstruction** — a grid is built from the page's line/rectangle primitives,
  which gives more accurate cell boundaries than default PDF table detection on
  complex documents.
- **Chapter grouping** — output can be grouped by the PDF's TOC, by your own list of
  chapter titles, or left flat.
- **Round-trip JSON** — `save_json` / `load_json` helpers; the resulting file is
  meant to be edited.
- **Configurable writer** — global defaults (`size`, `font`, `align_vert`, `area_color`, ...)
  can be overridden per-call via kwargs, or per-element via a `kwargs` key inside the JSON.
- **Auto-dispatch** — `writer.add(element)` picks the right renderer based on the element's `type`.

## Installation

- console
```console
pip install git+https://github.com/BogatirevAS/py-pdfroundtrip.git@master
```
```console
pip install git+https://github.com/BogatirevAS/py-pdfroundtrip.git@0.1.0
```

- requirements.txt
```requirements
pdfroundtrip @ git+https://github.com/BogatirevAS/py-pdfroundtrip.git@master
```
```requirements
pdfroundtrip @ git+https://github.com/BogatirevAS/py-pdfroundtrip.git@0.1.0
```

## Examples

1. Extracting
   ```python
   from pdfroundtrip.extractor import PdfExtractor, ModeEnum, ResultDataEnum
   from pdfroundtrip import save_json
   
   with PdfExtractor("input.pdf", init_doc_fonts=True) as extractor:
       collector = extractor.extract(
           pages=None,               # None = all pages, or int / list[int]
           drawing_types=["l", "re"],
           result_data=None,         # None = the default set of fields
       )
   
       data = collector.to(
           "dict",
           mode=ModeEnum.CHAPTERS_TYPE,
           chapters=["Summary", "Risks", "Financials"],  # optional, by default try extract toc of doc
       )
   
       save_json(data, "output.json")
   ```
2. Writing
   ```python
   from pdfroundtrip import load_json
   from pdfroundtrip.writer import StyleSwitch, PDFWriter, TextAlignV
   
   data = load_json("output.json")
   
   with PDFWriter(size=10, align_vert=TextAlignV.CENTER) as writer:
       for chapter in data.values():
           writer.add_chapter(
               chapter,
               min_area=0.2,
               font=StyleSwitch.DISABLE,   # ignore the element's own font
               size=StyleSwitch.DISABLE,   # ... and size
               area=StyleSwitch.DISABLE,   # ... and area
           )
       writer.save("output.pdf", open_=True)
   ```

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0-only)**. See the [LICENSE](LICENSE.txt) file for the full text.

### Third-party components and notices

This project depends on and/or contains code derived from components licensed under AGPL-3.0. All original copyright notices and license terms are preserved.

- **PyMuPDF** / **MuPDF**: Copyright (C) Artifex Software, Inc. Licensed under AGPL-3.0. A commercial license is also available from Artifex. See [PyMuPDF Licensing](https://pymupdf.io/licensing) for details.
- **pymupdf4llm**: Copyright (C) Artifex Software, Inc. Licensed under AGPL-3.0.
- **pymupdf-layout**: Copyright (C) Artifex Software, Inc. Licensed under AGPL-3.0.

For a full list of third-party notices, see the [NOTICE](NOTICE.txt) file.
