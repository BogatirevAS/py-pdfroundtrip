from typing import Any
from pymupdf import TextWriter, Point
from logger import LoggerMixin
from rgb_tuple import RGBTuple

from pdfroundtrip.writer.domain.models import Token
from pdfroundtrip.writer.core.page_manager import PageManager


class TextRenderer(LoggerMixin):
    def __init__(self, page_manager: PageManager, color: Any = (0.0, 0.0, 0.0)):
        self.page_manager = page_manager
        self.pos = Point()
        self.color = RGBTuple(color)
        self._text_writers = {}

    def flush(self):
        self.logger.debug("Flush text")
        for tw in self._text_writers.values():
            tw: TextWriter
            tw.write_text(self.page_manager.page)
        self._text_writers.clear()

    def _get_text_writer(self, color: Any = None) -> TextWriter:
        color = RGBTuple(color if color is not None else self.color)
        if color.int_tuple not in self._text_writers:
            self._text_writers[color.int_tuple] = TextWriter(
                page_rect=self.page_manager.page_rect,
                color=color.float_tuple,
            )
        return self._text_writers[color.int_tuple]

    def add(self, tokens: list[Token], pos: Point):
        self.pos = pos
        for span in tokens:
            text_writer = self._get_text_writer(span.style.color)
            self.logger.debug(f"Add {span} to {self.pos}")
            text_writer.append(
                pos=self.pos,
                text=span.text,
                font=span.style.font,
                fontsize=span.style.size,
            )
            self.pos = text_writer.last_point
        return self.pos
