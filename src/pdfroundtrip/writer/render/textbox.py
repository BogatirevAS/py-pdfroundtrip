from pymupdf import Rect
from logger import LoggerMixin, LogLevel

from pdfroundtrip.writer.render.base.abc import AbstractRenderer, SettingsProtocol
from pdfroundtrip.writer.render.base.graphic import GraphicRenderer
from pdfroundtrip.writer.render.base.text import TextRenderer
from pdfroundtrip.writer.core.coord_manager import CoordManager
from pdfroundtrip.writer.domain.models import Span, Paddings, Token, BlockSides
from pdfroundtrip.writer.utils.token import break_lines, calc_line_sizes


class TextboxRenderer(AbstractRenderer):
    def __init__(self,
                 text_renderer: TextRenderer,
                 graphic_renderer: GraphicRenderer,
                 coord_manager: CoordManager,
                 spans: list[Span],
                 settings: SettingsProtocol,
                 ):
        super().__init__([], coord_manager, settings)
        self.text_renderer = text_renderer
        self.graphic_renderer = graphic_renderer
        self.text_area = Rect(settings.area.x0 + settings.line_width.left + settings.paddings.left,
                              settings.area.y0 + settings.line_width.top + settings.paddings.top,
                              settings.area.x1 - settings.line_width.left - settings.paddings.left,
                              settings.area.y1 - settings.line_width.top - settings.paddings.top)
        self._rows_limits = []
        lines = break_lines(spans, self.text_area.width)
        if settings.split_lines:
            self._rows_limits = [0, len(lines)]
        else:
            lines = [lines]
        self._cur_line = 0
        self.lines = lines
        self._vert_coords = []
        self._horiz_coords = [self.settings.area.x0, self.settings.area.x1]

    def _add_line(self, line_width: float):
        self.logger.debug("Add line coord")
        self._vert_coords.append(self.coord_manager.cursor.y)
        self.coord_manager.advance_cursor(line_width)

    def _render_lines(self):
        self.logger.debug(f"Prepare coords: vert={self._vert_coords}, horiz={self._horiz_coords}")
        if self.settings.fill_color is not None:
            self.graphic_renderer.add_rect(rect=Rect(self._horiz_coords[0],
                                                     self._vert_coords[0],
                                                     self._horiz_coords[-1],
                                                     self._vert_coords[-1]),
                                           width=0,
                                           fill=self.settings.get_fill_color(), fill_opacity=self.settings.fill_opacity)
        lines = []
        if self.settings.line_width.left:
            x = self._horiz_coords[0] + self.settings.line_width.left / 2
            lines.append({
                "p1": (x, self._vert_coords[0]),
                "p2": (x, self._vert_coords[-1]),
                "color": self.settings.line_color.left,
                "width": self.settings.line_width.left,
            })
        if self.settings.line_width.right:
            x = self._horiz_coords[-1] - self.settings.line_width.left / 2
            lines.append({
                "p1": (x, self._vert_coords[0]),
                "p2": (x, self._vert_coords[-1]),
                "color": self.settings.line_color.right,
                "width": self.settings.line_width.right,
            })
        if self.settings.line_width.top:
            y = self._vert_coords[0] + self.settings.line_width.top / 2
            lines.append({
                "p1": (self._horiz_coords[0], y),
                "p2": (self._horiz_coords[-1], y),
                "color": self.settings.line_color.top,
                "width": self.settings.line_width.top,
            })
        if self.settings.line_width.bottom:
            y = self._vert_coords[-1] - self.settings.line_width.bottom / 2
            lines.append({
                "p1": (self._horiz_coords[0], y),
                "p2": (self._horiz_coords[-1], y),
                "color": self.settings.line_color.bottom,
                "width": self.settings.line_width.bottom,
            })
        for line in lines:
            self.graphic_renderer.add_line(**line)
        self._vert_coords.clear()

    def _is_row_limit(self, offset=0):
        return not self._rows_limits or (self._cur_line + offset in self._rows_limits)

    def add(self) -> bool | None:
        if not self.line:
            return None
        line = self.line if not self.settings.split_lines else [self.line]
        line_sizes = LinesSizes(line, self.settings.line_height, self.settings.paddings, self.settings.line_width)
        self.logger.debug("Try add line")
        if self._is_row_limit():
            if self.coord_manager.ensure_space(line_sizes.unsure_space()):
                self._add_line(self.settings.line_width.top)
                self.coord_manager.advance_cursor(self.settings.paddings.top)
            else:
                return False
        elif not self.coord_manager.ensure_space(line_sizes.unsure_space(False, False)):
            return False
        for i, l in enumerate(line):
            ls = line_sizes.lines[i]
            self.coord_manager.advance_cursor(ls.size)
            pos = self.coord_manager.get_pos(align_horiz=self.settings.align_horiz, total_width=ls.width,
                                             rect=self.text_area, align_vert=self.settings.align_vert,
                                             descender=ls.descender, size=ls.size, height=ls.height)
            self.text_renderer.add(l, pos)
        if self._is_row_limit(1):
            self.coord_manager.advance_cursor(self.settings.paddings.bottom)
        self.pop()
        self._cur_line += 1
        return True

    def flush(self):
        if not self._is_row_limit():
            self._rows_limits.append(self._cur_line)
            self.coord_manager.advance_cursor(self.settings.paddings.bottom)
        if self._vert_coords:
            self._add_line(self.settings.line_width.bottom)
            self._render_lines()


class LineSizes:
    def __init__(self, line: list[Token], line_height: float):
        self.height, self.width, self.descender, self.size = calc_line_sizes(line, line_height)


class LinesSizes(LoggerMixin):
    def __init__(self, lines: list[list[Token]], line_height: float,
                 paddings: Paddings, line_width: BlockSides):
        self.lines = [LineSizes(line, line_height) for line in lines]
        self._paddings = paddings
        self._line_width = line_width
        self._text_height = sum([rl.size for rl in self.lines])

    def unsure_space(self, top_line=True, top_padding=True):
        paddings_height = self._paddings.bottom
        if top_padding:
            paddings_height += self._paddings.top
        lines = self._line_width.bottom
        if top_line:
            lines += self._line_width.top
        res = self._text_height + lines + paddings_height
        if self.logger.isEnabledFor(LogLevel.DEBUG):
            self.logger.debug(f"{self._text_height} + {lines} + {paddings_height} = {res}")
        return res
