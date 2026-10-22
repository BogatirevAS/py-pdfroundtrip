from typing import Optional, Sequence
from pymupdf import Rect
from logger import LogLevel

from pdfroundtrip.extractor.collectors.base import AbstractCollector, CellCollector
from pdfroundtrip.extractor.domain.enums import ResultDataEnum, CollectorTypeEnum
from pdfroundtrip.extractor.utils import is_rect_child, nearest_coord, is_title
from pdfroundtrip.domain.enums import JsonKey
from pdfroundtrip.utils.fonts import DocumentFonts


class TableCollector(AbstractCollector):
    def __init__(self, area: Rect, xp: list[float], yp: list[float],
                 doc_fonts: DocumentFonts = None,
                 special_separators: list[str] = None):
        self._type = CollectorTypeEnum.TABLE
        self.area = area
        self.xp = xp
        self.yp = yp
        self.row_keys = yp[:-1]
        self.col_keys = xp[:-1]
        self.rows: dict[float, dict[float, CellCollector]] = {}
        self._data: dict[float, dict[float, CellCollector]] = {}
        self._headers = None
        self._normalized_data = None
        for yi, y in enumerate(self.row_keys):
            self.rows[y] = cells = {}
            for xi, x in enumerate(self.col_keys):
                cells[x] = CellCollector(Rect(x, y, xp[xi + 1], yp[yi + 1]), doc_fonts, special_separators)
        self._merged = []

    @property
    def type(self):
        return self._type

    @property
    def headers(self):
        if self._headers is None:
            self._headers = {}
            has_headers = False
            if len(self.data[0]) > 2:
                has_headers = True
            elif (len(self.data) == 2
                  and self.data[0][0].text and not self.data[0][0].text.isnumeric()
                  and self.data[0][1].text and not self.data[0][1].text.isnumeric()):
                if is_title(self.data[0][0].spans[0]):
                    if is_title(self.data[0][1].spans[0]):
                        has_headers = True
                elif self.data[1][0].text and self.data[1][0].text.isnumeric():
                    has_headers = True
            if has_headers:
                self._headers = {k: v.text for k, v in self.data[0].items()}
        return self._headers

    @property
    def data(self):
        if self._normalized_data is None:
            self._normalized_data = {}
            ri = 0
            for rk, cells in self.rows.items():
                if rk in self._data:
                    self._normalized_data[ri] = {}
                    for ci, ck in enumerate(cells):
                        self._normalized_data[ri][ci] = cells[ck]
                    ri += 1
        return self._normalized_data

    def get_text_row(self, i):
        return [v.text for v in self.data[i].values()]

    def _to(self, result_data: Optional[Sequence[ResultDataEnum]] = None):
        if result_data is None:
            result_data = list(ResultDataEnum)
        temp = {}
        if ResultDataEnum.TYPE in result_data:
            temp[JsonKey.TYPE] = self.type
        return temp

    def to_dict(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        temp = self._to(result_data)
        data = {rk: {ck: cell.to_dict(result_data) for ck, cell in cells.items()} for rk, cells in self.data.items()}
        temp.update({
            JsonKey.HEADER: data.pop(0) if self.headers else None,
            JsonKey.BODY: data,
        })
        return temp

    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        temp = self._to(result_data)
        data = [[cell.to_list(result_data) for cell in cells.values()] for cells in self.data.values()]
        temp.update({
            JsonKey.HEADER: data.pop(0) if self.headers else None,
            JsonKey.BODY: data,
        })
        return temp

    def add_span(self, span: dict) -> Optional["CellCollector"]:
        bbox = Rect(span["bbox"])
        text = span["text"]
        if not is_rect_child(self.area, bbox):
            self.logger.debug(f'"{text}" not included in the table area {self.area}, bbox: {bbox}')
            return None

        nearest_y = nearest_coord(self.row_keys, bbox.y0)
        nearest_x = nearest_coord(self.col_keys, bbox.x0)
        cell = self.rows[nearest_y][nearest_x]
        if is_rect_child(cell.area, bbox):
            cell.add_span(span)
            if self._data.get(nearest_y) is None:
                self._data[nearest_y] = {}
            self._data[nearest_y][nearest_x] = cell
            self.rows[nearest_y][nearest_x] = cell
            self.logger.debug(f'"{text}" add to table cell {cell.area}, bbox: {bbox}')
            return cell
        else:
            self.logger.debug(f'"{text}" not included in the cell area {cell.area}, bbox: {bbox}')
            return None

    def merge(self, collector: "TableCollector") -> Optional["TableCollector"]:
        if self.logger.isEnabledFor(LogLevel.DEBUG):
            self.logger.debug(f"Try merge to table with first row {self.get_text_row(0)}")
        if not isinstance(collector, TableCollector):
            self.logger.debug(f"Type {type(collector)} can't merged")
            return None
        if not collector.headers == self.headers:
            self.logger.debug(f"Headers mismatch: {collector.headers} != {self.headers}")
            return None
        if not collector.col_keys == self.col_keys:
            self.logger.debug(f"Col keys mismatch: {collector.col_keys} != {self.col_keys}")
            return None

        rows_before = len(self.data)
        self._merged.append(collector)
        merge_rows = False
        if len(self.headers) > 2:
            for k, v in collector.data[0].items():
                if not v.text:
                    self.logger.debug(f"Found empty cell by index \"{k}\" in {len(self.headers)} cols, merge rows")
                    merge_rows = True
                    break
        else:
            if not collector.data[0][0].text:
                self.logger.debug(f"Found empty cell by index \"0\" in 2 cols table, merge rows")
                merge_rows = True
        merge_row_index = 1 if self.headers and collector.headers == self.headers else 0
        if merge_row_index:
            self.logger.debug("Skip header row")
        if merge_rows:
            for k, v in collector.data[merge_row_index].items():
                if v.text:
                    nd_index = len(self._normalized_data)-1
                    for s in v.spans:
                        self._normalized_data[nd_index][k].add_span(s)
                        self.logger.debug(f"Merged cell: \"{self._normalized_data[nd_index][k].text}\"")
            merge_row_index += 1
        for ri, cells in collector.data.items():
            if ri < merge_row_index:
                continue
            self._normalized_data[len(self._normalized_data)] = cells
        if self.logger.isEnabledFor(LogLevel.DEBUG):
            self.logger.debug(f"Merged table by headers {self.headers} "
                              f"between {self.get_text_row(rows_before-1)} and {self.get_text_row(rows_before)}, "
                              f"rows: {rows_before} -> {len(self._normalized_data)}")
        return self
