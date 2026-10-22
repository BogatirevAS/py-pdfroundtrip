from typing import Sequence
from pymupdf import Rect
from logger import LoggerMixin

from pdfroundtrip.writer.domain.enums import RectType


def get_cell_rects(rect: Rect,
                   cols: int = None, rows: int = None,
                   x: int = None, y: int = None,
                   gap_x: float = 0.0, gap_y: float = 0.0,
                   ) -> Rect | list[Rect] | dict[int, dict[int, Rect]]:
    cols = cols or 1
    rows = rows or 1
    width = (rect.width - gap_x * (cols - 1)) / cols
    height = (rect.height - gap_y * (rows - 1)) / rows
    cells = {i: {} for i in range(rows)}
    for r in range(rows):
        for c in range(cols):
            x0 = rect.x0 + c * (width + gap_x)
            y0 = rect.y0 + r * (height + gap_y)
            x1 = x0 + width
            y1 = y0 + height
            cells[r][c] = Rect(x0, y0, x1, y1)
    if x is None and y is None:
        return cells
    elif x is None:
        return list(cells[y].values())
    elif y is None:
        return [r[x] for r in cells.values()]
    return cells[y][x]


def get_cell_rects_with_weights(rect: Rect,
                                cols: int = None, rows: int = None,
                                x: int = None, y: int = None,
                                gap_x: float = 0.0, gap_y: float = 0.0,
                                col_weights: Sequence[float] = None,
                                row_weights: Sequence[float] = None,
                                ) -> Rect | list[Rect] | dict[int, dict[int, Rect]]:
    cols = cols or 1
    rows = rows or 1
    col_weights = col_weights or [1.0] * cols
    row_weights = row_weights or [1.0] * rows
    total_width = sum(col_weights)
    total_height = sum(row_weights)
    width_available = rect.width - gap_x * (cols - 1)
    height_available = rect.height - gap_y * (rows - 1)
    widths = [width_available * (w / total_width) for w in col_weights]
    heights = [height_available * (h / total_height) for h in row_weights]
    cells = {}
    y0 = rect.y0
    for r in range(rows):
        cells[r] = {}
        x0 = rect.x0
        y1 = y0 + heights[r]
        for c in range(cols):
            x1 = x0 + widths[c]
            cells[r][c] = Rect(x0, y0, x1, y1)
            x0 = x1 + gap_x
        y0 = y1 + gap_y
    if x is None and y is None:
        return cells
    elif x is None:
        return list(cells[y].values())
    elif y is None:
        return [r[x] for r in cells.values()]
    return cells[y][x]


class CellSelector(LoggerMixin):
    _cache = {}

    def __init__(self, cols: int, rows: int,
                 x: int, y: int,
                 gap_x: float = None, gap_y: float = None,
                 col_weights: Sequence[float] = None,
                 row_weights: Sequence[float] = None,
                 rect: Rect | RectType = RectType.AREA,
                 ):
        self.rect = rect
        self.cols = cols
        self.rows = rows
        self.x = x
        self.y = y
        self.gap_x = gap_x
        self.gap_y = gap_y
        self.col_weights = col_weights
        self.row_weights = row_weights
        self._normalize_params()

    def _normalize_params(self):
        if self.cols == 1:
            if self.x != 0:
                self.logger.debug(f"Change x from {self.x} to 0")
                self.x = 0
            if self.gap_x != 0.0:
                self.logger.debug(f"Change gap_x from {self.gap_x} to 0.0")
                self.gap_x = 0.0
            if self.col_weights is not None:
                self.logger.debug(f"Change col_weights from {self.col_weights} to None")
                self.col_weights = None
        if self.rows == 1:
            if self.y != 0:
                self.logger.debug(f"Change y from {self.y} to 0")
                self.y = 0
            if self.gap_y != 0.0:
                self.logger.debug(f"Change gap_y from {self.gap_y} to 0.0")
                self.gap_y = 0.0
            if self.row_weights is not None:
                self.logger.debug(f"Change row_weights from {self.row_weights} to None")
                self.row_weights = None

    def _cache_key(self, rect: Rect, gap_x: float, gap_y: float, ):
        return (tuple(rect), self.cols, self.rows, self.x, self.y, gap_x, gap_y,
                tuple(self.col_weights) if self.col_weights is not None else None,
                tuple(self.row_weights) if self.row_weights is not None else None,
                )

    def select(self, rects: dict[RectType, Rect] = None, gap_x: float = None, gap_y: float = None, ):
        rects = rects or {}
        rect = self.rect if isinstance(self.rect, Rect) else rects.get(self.rect, None)
        gap_x = self.gap_x if self.gap_x is not None else gap_x or 0.0
        gap_y = self.gap_y if self.gap_y is not None else gap_y or 0.0
        if not rect:
            self.logger.error(f"No rect type {self.rect}")
            return None
        key = self._cache_key(rect, gap_x, gap_y)
        if key not in self._cache:
            self._cache[key] = get_cell_rects_with_weights(
                rect, self.cols, self.rows, self.x, self.y,
                gap_x, gap_y,
                self.col_weights, self.row_weights,
            )
            self.logger.debug(f"Cached {key}: {self._cache[key]}")
        return self._cache[key]

    @classmethod
    def TOP_LEFT(cls, gap_x: float = None, gap_y: float = None,
                 col_weights: tuple[float, float] = None, row_weights: tuple[float, float] = None,
                 rect: Rect | RectType = RectType.AREA, ):
        return CellSelector(2, 2, 0, 0, gap_x, gap_y, col_weights, row_weights, rect)

    @classmethod
    def TOP_RIGHT(cls, gap_x: float = None, gap_y: float = None,
                  col_weights: tuple[float, float] = None, row_weights: tuple[float, float] = None,
                  rect: Rect | RectType = RectType.AREA, ):
        return CellSelector(2, 2, 1, 0, gap_x, gap_y, col_weights, row_weights, rect)

    @classmethod
    def BOTTOM_LEFT(cls, gap_x: float = None, gap_y: float = None,
                    col_weights: tuple[float, float] = None, row_weights: tuple[float, float] = None,
                    rect: Rect | RectType = RectType.AREA, ):
        return CellSelector(2, 2, 0, 1, gap_x, gap_y, col_weights, row_weights, rect)

    @classmethod
    def BOTTOM_RIGHT(cls, gap_x: float = None, gap_y: float = None,
                     col_weights: tuple[float, float] = None, row_weights: tuple[float, float] = None,
                     rect: Rect | RectType = RectType.AREA, ):
        return CellSelector(2, 2, 1, 1, gap_x, gap_y, col_weights, row_weights, rect)

    @classmethod
    def CENTER(cls, gap_x: float = None, gap_y: float = None,
               col_weights: tuple[float, float, float] = None, row_weights: tuple[float, float, float] = None,
               rect: Rect | RectType = RectType.AREA, ):
        return CellSelector(3, 3, 1, 1, gap_x, gap_y, col_weights, row_weights, rect)


class ColSelector(CellSelector):
    def __init__(self, cols: int, x: int, gap: float = None,
                 weights: Sequence[float] = None, rect: Rect | RectType = RectType.AREA, ):
        super().__init__(cols, 1, x, 0, gap, 0.0, weights, None, rect)

    @classmethod
    def LEFT(cls, gap: float = None, weights: tuple[float, float] = None, rect: Rect | RectType = RectType.AREA):
        return ColSelector(2, 0, gap, weights, rect)

    @classmethod
    def RIGHT(cls, gap: float = None, weights: tuple[float, float] = None, rect: Rect | RectType = RectType.AREA):
        return ColSelector(2, 1, gap, weights, rect)

    @classmethod
    def CENTER(cls, gap: float = None, weights: tuple[float, float, float] = None, rect: Rect | RectType = RectType.AREA):
        return ColSelector(3, 1, gap, weights, rect)


class RowSelector(CellSelector):
    def __init__(self, rows: int, y: int, gap: float = None,
                 weights: Sequence[float] = None, rect: Rect | RectType = RectType.AREA):
        super().__init__(1, rows, 0, y, 0.0, gap, None, weights, rect)

    @classmethod
    def TOP(cls, gap: float = None, weights: tuple[float, float] = None, rect: Rect | RectType = RectType.AREA):
        return RowSelector(2, 0, gap, weights, rect)

    @classmethod
    def BOTTOM(cls, gap: float = None, weights: tuple[float, float] = None, rect: Rect | RectType = RectType.AREA):
        return RowSelector(2, 1, gap, weights, rect)

    @classmethod
    def CENTER(cls, gap: float = None, weights: tuple[float, float, float] = None, rect: Rect | RectType = RectType.AREA):
        return RowSelector(3, 1, gap, weights, rect)


def create_rects_matrix(horiz: list, vert: list):
    rows = len(vert) - 1
    cols = len(horiz) - 1
    matrix = []
    for i in range(rows):
        row_cells = []
        y1 = vert[i]
        y2 = vert[i + 1]
        for j in range(cols):
            x1 = horiz[j]
            x2 = horiz[j + 1]
            row_cells.append(Rect(x1, y1, x2, y2))
        matrix.append(row_cells)
    return matrix
