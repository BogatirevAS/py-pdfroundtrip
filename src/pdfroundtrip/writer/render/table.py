from pymupdf import Rect
from logger import LoggerMixin, LogLevel

from pdfroundtrip.writer.render.base.abc import AbstractRenderer, SettingsProtocol
from pdfroundtrip.writer.render.base.graphic import GraphicRenderer
from pdfroundtrip.writer.render.base.text import TextRenderer
from pdfroundtrip.writer.core.coord_manager import CoordManager
from pdfroundtrip.writer.domain.models import Span, Paddings, Token, BlockSides
from pdfroundtrip.writer.utils.rect import create_rects_matrix
from pdfroundtrip.writer.utils.token import break_lines, break_row_lines, calc_rol_line_sizes


class TableRenderer(AbstractRenderer):
    def __init__(self,
                 text_renderer: TextRenderer,
                 graphic_renderer: GraphicRenderer,
                 coord_manager: CoordManager,
                 header_spans: list[list[Span]],
                 body_spans: list[list[list[Span]]],
                 settings: SettingsProtocol,
                 header_settings: SettingsProtocol,
                 header_cell_kwargs: list,
                 body_cell_kwargs: list[list],
                 ):
        super().__init__([], coord_manager, settings)
        self.header_settings = header_settings
        self.text_renderer = text_renderer
        self.graphic_renderer = graphic_renderer

        self._header_cell_kwargs = header_cell_kwargs
        self._body_cell_kwargs = body_cell_kwargs

        all_spans = []
        if header_spans:
            all_spans.append(header_spans)
        all_spans.extend(body_spans)
        self._col_rects = self._create_col_rects(all_spans)
        self._header_lines = break_row_lines(header_spans, self._col_rects)
        self._header_rendered = False
        self._header_sizes = None
        rows = {i: break_row_lines(s, self._col_rects) for i, s in enumerate(body_spans)}
        self._rows_limits = []
        if not self.settings.split_lines:
            lines = list(rows.values())
        else:
            lines = []
            for r in rows.values():
                self._rows_limits.append(len(lines))
                lines.extend(r)
            self._rows_limits.append(len(lines))
        self.lines = lines
        self._cur_line = 0
        self._cur_row = 0
        self._vert_coords = []
        self._horiz_coords = [x.x0 - self.settings.paddings.left - self.settings.line_width.left for x in self._col_rects]
        self._horiz_coords.append(self._col_rects[-1].x1 + self.settings.paddings.right)

    @property
    def header(self):
        if not self._header_lines or self._header_rendered:
            return None
        return self._header_lines

    @property
    def header_sizes(self):
        if not self._header_lines:
            return None
        if not self._header_sizes:
            self._header_sizes = RowSizes(self._header_lines, self.header_settings.line_height,
                                          self.header_settings.paddings, self.header_settings.line_width)
        return self._header_sizes

    def _create_col_rects(self, spans: list[list[list[Span]]]) -> list[Rect]:
        self.logger.debug(f"Spans: {spans}")
        min_max_cols_width = calc_min_max_cols_width(spans)
        text_widths = calc_text_widths(self.settings.area.width, min_max_cols_width, self.settings.paddings,
                                       self.settings.line_width.left)
        return create_rects(self.settings.area, text_widths, self.settings.paddings, self.settings.line_width.left)

    def _add_text_row_line(self, line: dict[int, list[Token]], sizes: "RowLineSizes", cell_kwargs: list[dict],):
        for coln, l in line.items():
            self.text_renderer.add(l, self.coord_manager.get_pos(
                align_horiz=cell_kwargs[coln].get("align_horiz", self.settings.align_horiz),
                total_width=sizes.widths[coln],
                rect=self._col_rects[coln],
                align_vert=cell_kwargs[coln].get("align_vert", self.settings.align_vert),
                descender=sizes.descender,
                size=sizes.size,
                height=sizes.height
            ))

    def _add_line(self, line_width: float):
        self.logger.debug("Add line coord")
        self._vert_coords.append(self.coord_manager.cursor.y)
        self.coord_manager.advance_cursor(line_width)

    def _render_lines(self):
        self.logger.debug(f"Prepare coords: vert={self._vert_coords}, horiz={self._horiz_coords}")

        rects = create_rects_matrix(self._horiz_coords, self._vert_coords)
        self.logger.debug(f"Rects matrix: {rects}")
        if self.settings.fill_color is not None:
            for r, rect_line in enumerate(rects if not self._header_rendered else rects[1:]):
                for c, rect in enumerate(rect_line):
                    self.graphic_renderer.add_rect(rect=rect, width=0,
                                                   fill=self.settings.get_fill_color(r, c),
                                                   fill_opacity=self.settings.fill_opacity)

        top_width = self.settings.line_width.top
        left_width = self.settings.line_width.left
        if left_width:
            vert_lines = []
            for x in self._horiz_coords:
                tx = x + left_width / 2
                vert_lines.append(((tx, self._vert_coords[0 if not self._header_rendered else 1]), (tx, self._vert_coords[-1] + top_width)))
            self.logger.debug(f"Vertical lines: {len(vert_lines)}, {vert_lines}")
            for (p1, p2) in vert_lines:
                self.graphic_renderer.add_line(p1, p2, color=self.settings.line_color.left, width=left_width)
        if top_width:
            horiz_lines = []
            for y in self._vert_coords[0 if not self._header_rendered else 1:]:
                ty = y + top_width / 2
                horiz_lines.append(((self._horiz_coords[0], ty), (self._horiz_coords[-1] + left_width, ty)))
            self.logger.debug(f"Horizontal lines: {len(horiz_lines)}, {horiz_lines}")
            for (p1, p2) in horiz_lines:
                self.graphic_renderer.add_line(p1, p2, color=self.settings.line_color.top, width=top_width)

        if self._header_rendered:
            if self.header_settings.fill_color is not None:
                for r, rect_line in enumerate(rects if not self._header_rendered else rects[0:1]):
                    for c, rect in enumerate(rect_line):
                        self.graphic_renderer.add_rect(rect=rect, width=0,
                                                       fill=self.header_settings.get_fill_color(r, c),
                                                       fill_opacity=self.header_settings.fill_opacity)

            top_width = self.header_settings.line_width.top
            if left_width:
                vert_lines = []
                for x in self._horiz_coords:
                    tx = x + left_width / 2
                    vert_lines.append(((tx, self._vert_coords[0]), (tx, self._vert_coords[1] + top_width)))
                self.logger.debug(f"Header vertical lines: {len(vert_lines)}, {vert_lines}")
                for (p1, p2) in vert_lines:
                    self.graphic_renderer.add_line(p1, p2, color=self.header_settings.line_color.left, width=left_width)
            if top_width:
                horiz_lines = []
                for y in self._vert_coords[0:2]:
                    ty = y + top_width / 2
                    horiz_lines.append(((self._horiz_coords[0], ty), (self._horiz_coords[-1] + left_width, ty)))
                self.logger.debug(f"Header horizontal lines: {len(horiz_lines)}, {horiz_lines}")
                for (p1, p2) in horiz_lines:
                    self.graphic_renderer.add_line(p1, p2, color=self.header_settings.line_color.top, width=top_width)

        self._vert_coords.clear()

    def _is_row_limit(self, offset=0):
        return not self._rows_limits or (self._cur_line + offset in self._rows_limits)

    def add(self) -> bool | None:
        if not self.line:
            return None
        line = self.line if isinstance(self.line, list) else [self.line]
        line_sizes = RowSizes(line, self.settings.line_height, self.settings.paddings, self.settings.line_width)
        if self.header:
            self.logger.debug("Try add header")
            if self.coord_manager.ensure_space(self.header_sizes.unsure_space() + line_sizes.unsure_space(False)):
                self._add_line(self.header_settings.line_width.top)
                self.coord_manager.advance_cursor(self.header_settings.paddings.top)
                self.logger.debug("Start add header")
                for i, h in enumerate(self.header):
                    hsl = self.header_sizes.lines[i]
                    self.coord_manager.advance_cursor(hsl.size)
                    self._add_text_row_line(h, hsl, self._header_cell_kwargs)
                self.coord_manager.advance_cursor(self.header_settings.paddings.bottom)
            else:
                return False
        self.logger.debug("Try add line")
        if self.header:
            self._add_line(self.header_settings.line_width.top)
            self._header_rendered = True
            self.logger.debug("Header rendered")
            self.coord_manager.advance_cursor(self.settings.paddings.top)
        elif self._is_row_limit():
            if self.coord_manager.ensure_space(line_sizes.unsure_space()):
                self._add_line(self.settings.line_width.top)
                self.coord_manager.advance_cursor(self.settings.paddings.top)
            else:
                return False
        elif not self.coord_manager.ensure_space(line_sizes.unsure_space(False, False)):
            return False
        self.logger.debug("Start add line")
        for i, r in enumerate(line):
            rsl = line_sizes.lines[i]
            self.coord_manager.advance_cursor(rsl.size)
            self._add_text_row_line(r, rsl, self._body_cell_kwargs[self._cur_row])
        if self._is_row_limit(1):
            self.coord_manager.advance_cursor(self.settings.paddings.bottom)
            self._cur_row += 1
        self.pop()
        self._cur_line += 1
        return True

    def flush(self):
        self.logger.debug("Flush table")
        if not self._is_row_limit():
            self._rows_limits.append(self._cur_line)
            self.coord_manager.advance_cursor(self.settings.paddings.bottom)
        if self._vert_coords:
            self._add_line(self.settings.line_width.top)
            self._render_lines()
        self._header_rendered = False


class RowLineSizes:
    def __init__(self, line: dict[int, list[Token]], line_height: float):
        self.height, self.widths, self.descender, self.size = calc_rol_line_sizes(line, line_height)


class RowSizes(LoggerMixin):
    def __init__(self, row: list[dict[int, list[Token]]], line_height: float,
                 paddings: Paddings, line_width: BlockSides):
        self.lines = [RowLineSizes(line, line_height) for line in row]
        self._paddings = paddings
        self._line_width = line_width
        self._text_height = sum([rl.size for rl in self.lines])

    def unsure_space(self, top_line=True, top_padding=True):
        paddings_height = self._paddings.bottom
        if top_padding:
            paddings_height += self._paddings.top
        lines = 1
        if top_line:
            lines += 1
        res = self._text_height + lines * self._line_width.top + paddings_height
        if self.logger.isEnabledFor(LogLevel.DEBUG):
            self.logger.debug(f"{self._text_height} + {lines * self._line_width.top} + {paddings_height} = {res}")
        return res


def create_rects(rect: Rect, text_widths: dict[int, float], paddings: Paddings, line_width: float) -> list[Rect]:
    y0 = rect.y0 + line_width + paddings.top
    y1 = rect.y1 - line_width - paddings.bottom
    x = rect.x0 + line_width + paddings.left
    col_rects = []
    for w in text_widths.values():
        col_rects.append(Rect(x, y0, x + w, y1))
        x += w + paddings.right + line_width + paddings.left
    return col_rects


def calc_text_widths(max_width: float, cols_width: dict[int, list[float]], paddings: Paddings, line_width: float):
    ncols = len(cols_width)
    available_width = max_width - ncols * (paddings.left + paddings.right) - (ncols + 1) * line_width
    banned_keys = []
    res = {}
    recalc = True
    while recalc:
        recalc = False
        temp_widths = {}
        temp_available_width = available_width
        for i, (min_w, max_w) in cols_width.items():
            if i not in banned_keys:
                temp_widths[i] = max_w
            else:
                temp_available_width -= min_w
        sum_width = sum(temp_widths.values())
        props = {i: w / sum_width * temp_available_width for i, w in temp_widths.items()}
        for i, p in props.items():
            if p < cols_width[i][0]:
                res[i] = cols_width[i][0]
                banned_keys.append(i)
                recalc = True
            else:
                res[i] = p
    return res


def calc_min_max_cols_width(spans: list[list[list[Span]]]) -> dict[int, list[float]]:
    ncols = len(spans[0])
    cols_min_max = {}
    for i in range(ncols):
        cols_min_max[i] = [0.0, 0.0]
    for row in spans:
        for i in range(ncols):
            min_max = calc_min_max_cell_width(row[i])
            for j, m in enumerate(min_max):
                if m > cols_min_max[i][j]:
                    cols_min_max[i][j] = m
    return cols_min_max


def calc_min_max_cell_width(spans: list[Span]) -> tuple[float, float]:
    lines = break_lines(spans, None, False)
    min_w = 0.0
    max_w = 0.0
    for line in lines:
        cur_width = 0.0
        for token in line:
            if token.width > min_w:
                min_w = token.width
            cur_width += token.width
        if cur_width > max_w:
            max_w = cur_width
    return min_w, max_w
