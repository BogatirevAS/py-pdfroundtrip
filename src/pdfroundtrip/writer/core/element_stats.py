from pymupdf import Point

from pdfroundtrip.writer.domain.models import ElementStats
from pdfroundtrip.domain.enums import TextTypeEnum


class ElementStatsCollector:
    def __init__(self):
        self.elements_stats: dict[int, list[ElementStats]] = {}
        self._cur: ElementStats | None = None

    def new(self, type_: TextTypeEnum, start_pos: Point):
        self._cur = ElementStats(type_, None, None, start_pos, None, None, None)

    def update_start(self, index: int = None, xref: int = None, pos: Point = None):
        add = False
        if self._cur.start_page is None:
            if pos is not None:
                self._cur.start_pos = pos
            if index is not None:
                self._cur.start_page = index
                self._cur.start_page_xref = xref
                add = True
        if xref is not None:
            if xref not in self.elements_stats:
                self.elements_stats[xref] = []
                add = True
            if add:
                self.elements_stats[xref].append(self._cur)

    def update_end(self, index: int, xref: int, pos: Point):
        self._cur.end_page = index
        self._cur.end_page_xref = xref
        self._cur.end_pos = pos
