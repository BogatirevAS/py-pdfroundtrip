import json
from pathlib import Path
from typing import Optional, Sequence
import pymupdf.layout
import pymupdf4llm
from pymupdf import Document
from logger import LoggerMixin

from pdfroundtrip.extractor.collectors import ResultCollector
from pdfroundtrip.extractor.domain.enums import ResultDataEnum, ModeEnum
from pdfroundtrip.extractor.page import PageExtractor, PageExtractorDebug
from pdfroundtrip.extractor.utils import pymupdf_deepcopy_patch
from pdfroundtrip.utils.fonts import DocumentFonts
from pdfroundtrip.utils.utils import open_file


pymupdf_deepcopy_patch()


class PdfExtractorDebug(LoggerMixin):
    def __init__(self, doc: Document, data: ResultCollector, **kwargs):
        self._doc = doc
        self._data = data
        self._kwargs = kwargs
        self._page_debug: dict[int, PageExtractorDebug] = {}

    @property
    def doc(self):
        return self._doc

    @property
    def data(self):
        return self._data

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def page_debug(self):
        return self._page_debug

    def _add_page_debug(self, pno, debug: PageExtractorDebug):
        self._page_debug[pno] = debug

    def draw_doc(self, path: Path,
                 cluster_drawings=True,
                 drawings=True, drawing_types: Optional[Sequence[str]] = ("l", "re"),
                 table_areas=True,
                 open_=True,
                 ):
        doc = pymupdf.open()
        pages = list(self.page_debug.keys())
        for pno in pages:
            doc.insert_pdf(self.doc, from_page=pno, to_page=pno)
        for pno, debug in enumerate(self.page_debug.values()):
            debug.draw(
                page=doc.load_page(pno),
                cluster_drawings=cluster_drawings,
                drawings=drawings,
                drawing_types=drawing_types,
                table_areas=table_areas
            )
        doc.save(path, garbage=4, clean=True, deflate=True, deflate_images=True, deflate_fonts=True)
        doc.close()
        if open_:
            open_file(path)


class PdfExtractor(LoggerMixin):
    def __init__(self, path: Path, init_doc_fonts=True):
        self.logger.debug(f"Open doc: {path}")
        if not isinstance(path, Path) or path.exists() and not path.is_file():
            self.logger.error("No file path")
            raise ValueError("No file path")
        self.doc = pymupdf.open(path)
        self.doc_fonts = None if not init_doc_fonts else DocumentFonts(self.doc)
        self._debug = None

    @property
    def debug(self) -> PdfExtractorDebug:
        return self._debug

    def __enter__(self) -> "PdfExtractor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.logger.debug("Close doc")
        self.doc.close()

    # The following method is adapted from pymupdf4llm (helpers/document_layout.py).
    # Original code: Copyright (C) Artifex Software, Inc.
    # Licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
    # See the NOTICE file for details.
    def pno_list(self, pages: int | list[int] = None):
        if pages is None:
            page_filter = range(self.doc.page_count)
        elif isinstance(pages, int):
            while pages < 0:
                pages += self.doc.page_count
            page_filter = [pages]
        elif not hasattr(pages, "__getitem__"):
            raise ValueError("'pages' parameter must be an int, or a sequence of ints")
        else:
            page_filter = sorted(set(pages))
        if (
                not all(isinstance(p, int) for p in page_filter)
                or page_filter[-1] >= self.doc.page_count
        ):
            raise ValueError(
                f"'pages' parameter must be None, int, or a sequence of ints less than {self.doc.page_count}."
            )
        return page_filter

    def to_json(self, pages: int | list[int] = None, **kwargs) -> str:
        return pymupdf4llm.to_json(
            self.doc,
            pages=pages,
            **kwargs
        )

    def to_dict(self, pages: int | list[int] = None, **kwargs) -> dict:
        return json.loads(self.to_json(pages=pages, **kwargs))

    def to_text(self, pages: int | list[int] = None, **kwargs) -> str:
        return pymupdf4llm.to_text(
            self.doc,
            pages=pages,
            **kwargs
        )

    def to_markdown(self, pages: int | list[int] = None, **kwargs) -> str:
        return pymupdf4llm.to_markdown(
            self.doc,
            pages=pages,
            **kwargs
        )

    def extract(self, pages: int | list[int] = None,
                drawing_types: Optional[Sequence[str]] = ("l", "re"),
                cluster_drawings_min_dimension: Optional[float] = 10,
                exclude_images=True,
                exclude_page_boundaries=True,
                line_tolerance=5,
                delete_one_cell_table=True,
                special_separators: list[str] = None,
                result_data: Optional[Sequence[ResultDataEnum]] = None,
                mode: ModeEnum = ModeEnum.CHAPTERS_TYPE,
                chapters: list[str] = None,
                chapters_nested: bool = False,
                chapters_max_level: Optional[int] = None,
                ) -> ResultCollector:
        chapters = chapters if chapters is not None else self.doc.get_toc()
        result_collector = ResultCollector(result_data=result_data, mode=mode, chapters=chapters,
                                           chapters_nested=chapters_nested, chapters_max_level=chapters_max_level)
        self._debug = PdfExtractorDebug(
            doc=self.doc,
            data=result_collector,
            pages=pages,
            drawing_types=drawing_types,
            cluster_drawings_min_dimension=cluster_drawings_min_dimension,
            exclude_images=exclude_images,
            exclude_page_boundaries=exclude_page_boundaries,
            line_tolerance=line_tolerance,
            delete_one_cell_table=delete_one_cell_table,
            result_data=result_data,
            special_separators=special_separators,
        )
        pno_list = self.pno_list(pages)

        for pno in pno_list:
            self.logger.info(f"Start page {pno}")
            page = self.doc.load_page(pno)
            page_data = self.to_dict(pages=pno)
            page_extractor = PageExtractor(page, self.doc_fonts, special_separators)
            page_result_collector = page_extractor.extract(
                page_data=page_data,
                drawing_types=drawing_types,
                cluster_drawings_min_dimension=cluster_drawings_min_dimension,
                exclude_images=exclude_images,
                exclude_page_boundaries=exclude_page_boundaries,
                line_tolerance=line_tolerance,
                delete_one_cell_table=delete_one_cell_table,
            )
            result_collector.add_page(pno, page_result_collector)
            self.debug._add_page_debug(pno, page_extractor.debug)
        return result_collector
