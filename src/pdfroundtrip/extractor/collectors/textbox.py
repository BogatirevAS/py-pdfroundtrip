from typing import Optional, Sequence
from pymupdf import Rect

from pdfroundtrip.extractor.collectors.base import AbstractCollector, PrimitiveCollector
from pdfroundtrip.extractor.domain.enums import ResultDataEnum, CollectorTypeEnum
from pdfroundtrip.extractor.utils import is_close_lines, is_one_line, is_list_item, is_subtitle
from pdfroundtrip.utils.fonts import DocumentFonts


class TextboxCollector(AbstractCollector):
    def __init__(self, span: dict, mediabox: Rect,
                 doc_fonts: DocumentFonts = None,
                 special_separators: list[str] = None):
        span_bbox = Rect(span["bbox"])
        textbox_bbox = Rect(span_bbox.x0, mediabox.y0, mediabox.x1 - (span_bbox.x0 - mediabox.x0), mediabox.y1)
        self.logger.debug(f"Create textbox_bbox: {span_bbox} + {mediabox} = {textbox_bbox}")
        self.data = PrimitiveCollector(CollectorTypeEnum.TEXTBOX, span, textbox_bbox, doc_fonts, special_separators)

    def to_dict(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        return self.data.to_dict(result_data)

    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        return self.data.to_list(result_data)

    def add_span(self, span: dict) -> Optional["TextboxCollector"]:
        skip = True
        if self.data:
            bbox = Rect(span["bbox"])
            prev_span = self.data.spans[-1]
            prev_bbox = Rect(prev_span["bbox"])

            if is_list_item(span["text"]):
                self.logger.debug("Merge spans by list item")
                skip = False
            elif is_one_line(prev_bbox, bbox):
                self.logger.debug("Merge spans by one line")
                skip = False
            elif is_subtitle(span):
                self.logger.debug("Skip subtitle span")
            elif is_close_lines(prev_bbox, bbox):
                self.logger.debug("Merge spans by close lines")
                skip = False
        if skip:
            self.logger.debug(f"Can't merge spans")
            return None
        self.data.add_span(span)
        return self

    def merge(self, collector: "TextboxCollector") -> Optional["TextboxCollector"]:
        return None
