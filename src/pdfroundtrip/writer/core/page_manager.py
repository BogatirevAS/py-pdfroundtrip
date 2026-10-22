from pymupdf import Rect, Page, Document
from logger import LoggerMixin

from pdfroundtrip.writer.domain.consts import A4


class PageManager(LoggerMixin):
    def __init__(self,
                 doc: Document,
                 page_size: tuple = A4,
                 margins: tuple[float, float, float, float] = (27.0, 12.0, 27.0, 12.0),
                 ):
        self.doc = doc
        self.page_size = page_size
        self.margins = margins
        self.page_rect = Rect(0, 0, page_size[0], page_size[1])
        self.area = Rect(0 + margins[0], 0 + margins[1], page_size[0] - margins[2], page_size[1] - margins[3])
        self.page: Page | None = None
        self.index = 0
        self._saved_index: int | None = None
        self._toc = {}
        if len(self.doc) == 0:
            self.new_page()

    @property
    def last_index(self) -> int:
        return len(self.doc) - 1

    @property
    def next_index(self) -> int:
        return self.index + 1

    @property
    def is_end(self) -> bool:
        return self.index == self.last_index

    @property
    def is_next_out_of_index(self) -> bool:
        return self.next_index > self.last_index

    def save_index(self):
        self.logger.debug(f"Save index {self.index}")
        self._saved_index = self.index

    def load_index(self):
        self.logger.debug(f"Load index {self._saved_index}")
        self.index = self._saved_index

    def new_page(self, index: int = -1):
        self.logger.debug("New page")
        self.page = self.doc.new_page(pno=index, width=self.page_size[0], height=self.page_size[1])
        self.index = self.last_index if index == -1 else index
        return self.page

    def go_to_page(self, index: int):
        self.logger.debug(f"Switch to page {index}")
        self.page = self.doc[index]
        self.index = index
        return self.page

    def go_to_end_page(self):
        self.go_to_page(self.last_index)
        return self.page

    def next_page(self):
        if self.is_next_out_of_index:
            return self.new_page()
        return self.go_to_page(self.next_index)

    def next_new_page(self):
        index = -1 if self.is_next_out_of_index else self.next_index
        return self.new_page(index)

    def add_title(self, level: int, text: str, index: int):
        page = self.doc[index]
        xref = page.xref
        self.logger.debug(f"Add title: level={level}, text=\"{text}\", index={index}, page={page.number}, xref={xref}")
        if xref not in self._toc:
            self._toc[xref] = []
        self._toc[xref].append([level, text])

    @property
    def xref_to_page(self) -> dict[int, int]:
        return {p.xref: p.number for p in self.doc}

    def save_toc(self):
        self.logger.debug(f"Try save toc")
        if not self._toc:
            return None
        xref_to_page = self.xref_to_page
        toc = []
        for xref, data in self._toc.items():
            page = xref_to_page.get(xref)
            if page is None:
                continue
            for level, text in data:
                toc.append([level, text, page + 1])
        self.logger.debug(f"Save toc: {toc}")
        self.doc.set_toc(toc)

    @property
    def xref(self):
        return self.xref_by_index(self.index)

    def xref_by_index(self, index: int):
        return self.doc[index].xref

    def index_by_xref(self, xref: int):
        return self.xref_to_page[xref]
