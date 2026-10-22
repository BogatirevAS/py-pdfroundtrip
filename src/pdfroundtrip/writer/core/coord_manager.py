from pymupdf import Rect, Point
from logger import LoggerMixin, LogLevel

from pdfroundtrip.writer.domain.enums import TextAlignH, TextAlignV


class CoordManager(LoggerMixin):
    def __init__(self, area: Rect):
        self.area = area
        self._cursor = self.area.top_left
        self._saved_cursors = {}

    @property
    def cursor(self):
        return Point(self._cursor)

    def ensure_space(self, needed_height: float):
        if self.logger.isEnabledFor(LogLevel.DEBUG):
            self.logger.debug(f"{self._cursor.y} + {needed_height} = {self._cursor.y + needed_height} <= {self.area.y1}")
        return self._cursor.y + needed_height <= self.area.y1

    def ensure_space_by_area(self, min_area: float):
        if 0.0 < min_area <= 1.0:
            height = self.area.height * min_area
        else:
            height = min_area
        self.logger.debug(f"{min_area} -> {height}")
        return self.ensure_space(height)

    def advance_cursor(self, dy: float):
        self._cursor.y += dy
        self.logger.debug(f"Advance cursor by {dy} to {self._cursor.y}")

    def reset(self):
        self.logger.debug(f"Reset cursor from {self._cursor} to {self.area.top_left}")
        self._cursor = self.area.top_left

    def to_end(self):
        if self._cursor != self.area.bottom_left:
            self.logger.debug(f"Move cursor from {self._cursor} to {self.area.bottom_left}")
            self._cursor = self.area.bottom_left

    def cursor_by_key(self, key: int | str = None):
        return Point(self._saved_cursors.get(key, self.area.top_left))

    def save_larger_cursor(self, key: int):
        if self._cursor.y > self.cursor_by_key(key).y:
            self.save_cursor(key)

    def save_cursor(self, key: int | str = None):
        self.logger.debug(f"Save cursor {self._cursor} by {key}")
        self._saved_cursors[key] = self.cursor

    def load_cursor(self, key: int | str = None):
        self.logger.debug(f"Load cursor {self.cursor_by_key(key)} by {key}")
        self._cursor = self.cursor_by_key(key)

    def calc_x_by_horiz_align(self, align: TextAlignH, total_width: float, rect: Rect = None):
        rect = rect or self.area
        if align == TextAlignH.RIGHT:
            start_x = rect.x0 + rect.width - total_width
        elif align == TextAlignH.CENTER:
            start_x = rect.x0 + (rect.width - total_width) / 2
        else:
            start_x = rect.x0
        self.logger.debug(f"Calc x for {align.name}: {rect.x0} -> {start_x}")
        return start_x

    def calc_y_by_vert_align(self, align: TextAlignV, descender: float, size: float, height: float):
        if align == TextAlignV.BOTTOM:
            y = self._cursor.y - descender
        elif align == TextAlignV.CENTER:
            y = self._cursor.y - descender - (size - height) / 2
        elif align == TextAlignV.TOP:
            y = self._cursor.y - descender - (size - height)
        else:
            y = self._cursor.y
        self.logger.debug(f"Calc y for {align.name}, descender={descender}, size={size}, height={height}: {self._cursor.y} -> {y}")
        return y

    def get_pos(self, align_horiz: TextAlignH, total_width: float, rect: Rect | None,
                align_vert: TextAlignV, descender: float, size: float, height: float):
        return Point(self.calc_x_by_horiz_align(align_horiz, total_width, rect),
                     self.calc_y_by_vert_align(align_vert, descender, size, height))
