from pathlib import Path
from typing import Any, Protocol
from pymupdf import Font, Document
from logger import LoggerMixin
from rgb_tuple import RGBTuple

from pdfroundtrip.writer.domain.models import Style, Span
from pdfroundtrip.utils.fonts import DocumentFonts, FontMatrix
from pdfroundtrip.utils.json import get_json_param
from pdfroundtrip.utils.utils import to_list
from pdfroundtrip.domain.enums import JsonKey, StyleSwitch, FontEnum


class DefaultProtocol(Protocol):
    @property
    def font(self) -> str | FontMatrix:
        pass

    def get_font(self, bold=False, italic=False) -> str:
        pass

    @property
    def size(self) -> float:
        pass

    @property
    def color(self) -> Any:
        pass

    @property
    def bold(self) -> bool:
        pass

    @property
    def italic(self) -> bool:
        pass


class StyleManager(LoggerMixin):
    def __init__(self,
                 doc: Document = None,
                 fonts: DocumentFonts | dict[str, Path | bytes | str | Font] | Path | str = None,
                 font_regular: str = FontEnum.HELVETICA_REGULAR,
                 font_bold: str = FontEnum.HELVETICA_BOLD,
                 font_italic: str = FontEnum.HELVETICA_ITALIC,
                 font_bold_italic: str = FontEnum.HELVETICA_BOLD_ITALIC,
                 size: float = 12,
                 color: Any = (0.0, 0.0, 0.0),
                 ):
        RGBTuple.init_default_colors()
        self.doc_fonts = fonts if isinstance(fonts, DocumentFonts) else DocumentFonts(doc, fonts, True)
        self.font_regular = self.doc_fonts.get(font_regular)
        self.font_bold = self.doc_fonts.get(font_bold)
        self.font_italic = self.doc_fonts.get(font_italic)
        self.font_bold_italic = self.doc_fonts.get(font_bold_italic)
        self._font_matrix = FontMatrix(self.font_regular, self.font_bold, self.font_italic, self.font_bold_italic)
        self.size = size
        self.color = RGBTuple(color)
        self._default_style = self.create_span("").style
        self._last_style = self.default_style

    @property
    def default_style(self) -> Style:
        return self._default_style

    @property
    def last_style(self) -> Style:
        return self._last_style

    def _get_span_param(self, name: JsonKey, styles: dict, default):
        return get_json_param(name=name, data=styles, default=default)

    def _find_font(self, font: str = None, bold=None, italic=None, default: DefaultProtocol = None,):
        if isinstance(font, str):
            font = self.doc_fonts.get(font) if font is not None else None
        else:
            font = None
        if not font:
            if default is not None:
                font = self.doc_fonts.get(default.get_font(bold if bold is not None else default.bold,
                                                           italic if italic is not None else default.italic))
            else:
                font = self._font_matrix.get(bold, italic)
        return font

    def _get_size(self, size: float = None, default: DefaultProtocol = None,):
        if size is None:
            size = default.size if default else self.size
        return size

    def _get_color(self, color: Any, default: DefaultProtocol = None,):
        if color is None:
            color = default.color if default else self.color
        return RGBTuple(color)

    def create_span(self, text: str,
                    font: str | StyleSwitch = None,
                    size: float | StyleSwitch = None,
                    color: Any | StyleSwitch = None,
                    bold: bool | StyleSwitch = None,
                    italic: bool | StyleSwitch = None,
                    default: DefaultProtocol = None,
                    styles: dict = None):
        font = self._get_span_param(JsonKey.FONT, styles, font)
        size = self._get_span_param(JsonKey.SIZE, styles, size)
        color = self._get_span_param(JsonKey.COLOR, styles, color)
        bold = self._get_span_param(JsonKey.BOLD, styles, bold)
        italic = self._get_span_param(JsonKey.ITALIC, styles, italic)

        font = self._find_font(font, bold, italic, default)
        size = self._get_size(size, default)
        color = self._get_color(color, default)
        res = Span(text=text, style=Style(font=font, size=size, color=color))
        return res

    def create_spans(self, data: str | list | dict,
                     font: str | StyleSwitch = None,
                     size: float | StyleSwitch = None,
                     color: Any | StyleSwitch = None,
                     bold: bool | StyleSwitch = None,
                     italic: bool | StyleSwitch = None,
                     default: DefaultProtocol = None,
                     ):
        self.logger.debug(f"data: {data}")
        spans = []
        if isinstance(data, str):
            spans.append(self.create_span(data, font, size, color, bold, italic, default))
        elif isinstance(data, list):
            for d in data:
                spans.append(self.create_span(d, font, size, color, bold, italic, default))
        elif isinstance(data, dict):
            texts = data.get(JsonKey.TEXTS)
            styles = data.get(JsonKey.STYLES)
            texts_v = to_list(texts)
            styles_v = to_list(styles)
            for i, t in enumerate(texts_v):
                s = styles_v[i] if styles_v else None
                spans.append(self.create_span(t, font, size, color, bold, italic, default, s))
        else:
            raise TypeError("Wrong data type for create spans")
        self.logger.debug(f"Result for {data.__class__.__name__} instance: {spans}")
        if spans:
            self._last_style = spans[-1].style
        return spans
