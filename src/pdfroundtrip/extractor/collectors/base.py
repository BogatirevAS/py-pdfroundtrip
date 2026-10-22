from abc import ABC, abstractmethod
from typing import Sequence, Optional
from pymupdf import Rect
from logger import LoggerMixin

from pdfroundtrip.extractor.domain.enums import ResultDataEnum, CollectorTypeEnum
from pdfroundtrip.extractor.utils import is_one_line, is_one_word, is_list_item, is_next_line, extract_span_styles
from pdfroundtrip.utils.fonts import DocumentFonts


class AbstractCollector(LoggerMixin, ABC):
    @abstractmethod
    def to_dict(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        pass

    @abstractmethod
    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> list:
        pass

    @abstractmethod
    def add_span(self, span: dict) -> "AbstractCollector":
        pass


class PrimitiveCollector(AbstractCollector):
    def __init__(self, type_: CollectorTypeEnum,
                 span: dict, area: Rect = None,
                 doc_fonts: DocumentFonts = None,
                 special_separators: list[str] = None):
        self.doc_fonts = doc_fonts
        self.special_separators = ['-', '/'] if special_separators is None else special_separators
        self._type = type_
        self.area = area
        self.text: str | None = None
        self.texts: list[str] | None = None
        self.spans: list[dict] | None = None
        if span:
            self.add_span(span)

    @property
    def type(self):
        return self._type

    @property
    def styles(self):
        if not self.spans:
            return None
        return [extract_span_styles(span) for span in self.spans]

    def to_dict(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        if result_data is None:
            result_data = list(ResultDataEnum)
        return {rd: temp for rd in result_data if (temp := getattr(self, rd, None)) is not None}

    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        return self.to_dict(result_data)

    def add_span(self, span: dict) -> "PrimitiveCollector":
        text = span["text"]
        bbox = Rect(span["bbox"])
        temp_texts = self.texts or []

        if len(temp_texts) > 0:
            if is_list_item(text):
                first_span = self.spans[0]
                first_bbox = Rect(first_span["bbox"])
                if is_one_line(first_bbox, bbox):
                    self.logger.debug("Insert list item at start")
                    self.spans.insert(0, span)
                    self.texts.insert(0, f"{text} ")
                    self.text = "".join(self.texts)
                    return self

            def prev_text():
                return temp_texts[-1]

            if prev_text().endswith(text):
                splitted = prev_text().split(text)
                temp_texts[-1] = "".join(splitted[0:-1])

            prev_span = self.spans[-1]
            prev_bbox = Rect(prev_span["bbox"])
            if is_one_line(prev_bbox, bbox):
                if prev_text()[-1] != ' ' and not is_one_word(prev_bbox, bbox):
                    temp_texts[-1] = f"{prev_text()} "
            elif is_next_line(prev_span, span, self.area, self.doc_fonts):
                if not (len(prev_text()) > 1 and prev_text()[-1] == ' ' and prev_text()[-2] in self.special_separators):
                    temp_texts[-1] = f"{prev_text().strip()}\n"
            elif prev_text()[-1] in self.special_separators:
                if prev_text()[-2] == ' ':
                    temp_texts[-1] = f"{prev_text()} "
            elif prev_text()[-1] != ' ':
                temp_texts[-1] = f"{prev_text()} "

        temp_texts.append(text)
        self.texts = temp_texts

        self.text = "".join(self.texts)

        temp_spans = self.spans or []
        temp_spans.append(span)
        self.spans = temp_spans

        return self


class CellCollector(PrimitiveCollector):
    def __init__(self, area: Rect, doc_fonts: DocumentFonts = None, special_separators: list[str] = None):
        super().__init__(CollectorTypeEnum.CELL, {}, area, doc_fonts, special_separators)
