from typing import Any
from pymupdf import Rect
from logger import LoggerMixin
from rgb_tuple import RGBTuple

from pdfroundtrip.writer.core.page_manager import PageManager


class GraphicRenderer(LoggerMixin):
    def __init__(self, page_manager: PageManager, line_width: float = 1.0, color: Any = (0.0, 0.0, 0.0)):
        self.page_manager = page_manager
        self.line_width = line_width
        self.color = RGBTuple(color)

    @property
    def page(self):
        return self.page_manager.page

    def add_image(self, rect: Rect, file, **kwargs):
        self.logger.debug(f"Add image to {rect}")
        return self.page.insert_image(rect, filename=file, **kwargs)

    def add_line(self, p1, p2, color: Any = None, width: float = None, **kwargs):
        self.logger.debug(f"Add line from {p1} to {p2}, color={color}, width={width}")
        return self.page.draw_line(p1=p1, p2=p2,
                                   color=RGBTuple(color if color is not None else self.color).float_tuple,
                                   width=width or self.line_width, **kwargs)

    def add_rect(self, rect: Rect, color: Any = None, width: float = None,
                 fill: Any = None, fill_opacity: float = None,
                 **kwargs):
        self.logger.debug(f"Add rect to {rect}, color={color}, width={width}, fill={fill}, fill_opacity={fill_opacity}")
        return self.page.draw_rect(rect=rect,
                                   color=RGBTuple(color if color is not None else self.color).float_tuple,
                                   fill=fill if fill is None else RGBTuple(fill).float_tuple,
                                   width=width if width is not None else self.line_width,
                                   fill_opacity=fill_opacity if fill_opacity is not None else 1,
                                   **kwargs)
