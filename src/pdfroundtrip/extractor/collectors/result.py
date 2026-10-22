from copy import deepcopy
from typing import Optional, Sequence, Literal
from pymupdf import Rect
from logger import LoggerMixin, LogLevel

from pdfroundtrip.extractor.collectors.chapter import ChapterGroupCollector, filter_duplicate_chapters
from pdfroundtrip.extractor.collectors.base import AbstractCollector
from pdfroundtrip.extractor.collectors.table import TableCollector
from pdfroundtrip.extractor.collectors.textbox import TextboxCollector
from pdfroundtrip.extractor.domain.enums import ResultDataEnum, ModeEnum
from pdfroundtrip.extractor.utils import is_rect_higher, is_rect_lower, is_title, is_subtitle
from pdfroundtrip.utils.fonts import DocumentFonts


class PageResultCollector(AbstractCollector):
    def __init__(self, table_areas: dict,
                 mediabox: Rect,
                 doc_fonts: DocumentFonts = None,
                 special_separators: list[str] = None):
        self.doc_fonts = doc_fonts
        self.special_separators = special_separators
        self.table_collectors: list[TableCollector] = self._create_table_collectors(table_areas)
        self.table_i = 0
        self.mediabox = mediabox
        self.data: list[AbstractCollector] | None = None
        self.current_textbox: TextboxCollector | None = None
        self.current_table: TableCollector | None = \
            self.table_collectors[self.table_i] if len(self.table_collectors) > 0 else None
        self.current: AbstractCollector | None = None

    def to_dict(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        return {i: collector.to_dict(result_data) for i, collector in enumerate(self.data)}

    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> list:
        return [collector.to_list(result_data) for collector in self.data]

    def _create_table_collectors(self, table_areas: dict):
        res = []
        for i, t in table_areas.items():
            res.append(TableCollector(*t.values(), self.doc_fonts, self.special_separators))
        return res

    def _add_textbox_span(self, span):
        if not self.current_textbox or self.current != self.current_textbox or self.current.add_span(span) is None:
            self.logger.debug(f'Append textbox: "{span["text"]}"')
            self.current_textbox = TextboxCollector(span, self.mediabox, self.doc_fonts, self.special_separators)
            self.current = self.current_textbox
            self.data.append(self.current)
        return self.current

    def _add_table_span(self, span):
        text = span["text"]
        span_bbox = Rect(span["bbox"])
        if self.current_table and is_rect_higher(span_bbox, self.current_table.area):
            self.logger.debug(f'Span is higher, add like text: "{text}"')
            return None
        else:
            while self.table_i < len(self.table_collectors):
                if is_rect_lower(span_bbox, self.table_collectors[self.table_i].area):
                    self.logger.debug("Span is lower, get next table")
                    self.table_i += 1
                else:
                    self.current_table = self.table_collectors[self.table_i]
                    break
            if self.table_i >= len(self.table_collectors):
                self.logger.debug(f'No tables, add like text: "{text}"')
                return None
            elif self.current_table.add_span(span) is None:
                self.logger.debug(f'Can\'t add to table, add like text: "{text}"')
                return None
        if self.current != self.current_table:
            self.current = self.current_table
            self.data.append(self.current)
        return self.current

    def add_span(self, span: dict) -> Optional["AbstractCollector"]:
        text = span["text"].strip()
        if text == "":
            self.logger.debug("Empty text, skip span")
            return None

        if not self._add_table_span(span):
            self._add_textbox_span(span)
        return self.current

    def fill_data(self, page_data: dict):
        self.data = []
        self.table_i = 0
        full_text = page_data["pages"][0]["fulltext"]
        for elem in full_text:
            for line in elem["lines"]:
                for span in line["spans"]:
                    self.add_span(span)
        return self


class ResultCollector(LoggerMixin):
    def __init__(self,
                 result_data: Optional[Sequence[ResultDataEnum]] = None,
                 mode: ModeEnum = ModeEnum.CHAPTERS,
                 chapters: list = None,
                 chapters_nested: bool = False,
                 chapters_max_level: Optional[int] = None,
                 ):
        self.result_data = result_data
        self.mode = mode
        self.chapters = chapters
        self.chapters_nested = chapters_nested
        self.chapters_max_level = chapters_max_level
        self.data: dict[int, PageResultCollector] = {}

    def _create_toc(self,
                    chapters: list | None,
                    chapters_nested: Optional[bool] = None,
                    chapters_max_level: Optional[int] = None) -> Optional[list[tuple[str, int]]]:
        chapters = chapters if chapters is not None else self.chapters
        if chapters is None:
            return None
        chapters_nested = chapters_nested if chapters_nested is not None else self.chapters_nested
        chapters_max_level = chapters_max_level if chapters_max_level is not None else self.chapters_max_level

        res = []
        for c in chapters:
            if isinstance(c, str):
                res.append((c, 1))
            elif isinstance(c, (tuple, list)):
                l = c[0]
                if chapters_max_level and l > chapters_max_level:
                    continue
                if not chapters_nested:
                    l = 1
                res.append((c[1], l))
        self.logger.debug(f"create toc: {chapters} -> {res}")
        return res

    def group_by_chapters(self,
                          chapters: Optional[list] = None,
                          chapters_nested: bool = None,
                          chapters_max_level: Optional[int] = None,
                          mode: ModeEnum = None) -> dict:
        toc = self._create_toc(chapters, chapters_nested, chapters_max_level)
        titles = [t[0] for t in toc] if toc is not None else None
        chapter_list = []
        chapter = ChapterGroupCollector(0)
        data = deepcopy(self.data)
        for pno, page in data.items():
            for i, value in enumerate(page.data):
                if isinstance(value, TextboxCollector) and is_title(value.data.spans[0]):
                    if titles is None:
                        if not is_subtitle(value.data.spans[0]):
                            chapter = ChapterGroupCollector(value.data.text.strip())
                    else:
                        if value.data.text.strip() in titles:
                            title_index = titles.index(value.data.text.strip())
                            titles.pop(title_index)
                            chapter = ChapterGroupCollector(*toc.pop(title_index))
                if not chapter_list or chapter != chapter_list[-1]:
                    chapter_list.append(chapter)
                elif i == 0 and chapter.last.merge(value):
                    continue
                chapter.add(value)

        if self.logger.isEnabledFor(LogLevel.DEBUG):
            self.logger.debug(f"Before filter: {[(c.title, c.level) for c in chapter_list]}")
        chapter_list = filter_duplicate_chapters(chapter_list)
        if self.logger.isEnabledFor(LogLevel.DEBUG):
            self.logger.debug(f"After filter: {[(c.title, c.level) for c in chapter_list]}")

        type_ = True if mode == ModeEnum.CHAPTERS_TYPE else False
        res = {}
        parent = [res]
        prev_ch: ChapterGroupCollector = None
        prev_obj: ChapterGroupCollector = None
        for i, ch in enumerate(chapter_list):
            ch_obj = ch.to_type() if type_ else ch

            if prev_ch is None:
                res[ch.title] = ch_obj
            else:
                if ch.level > prev_ch.level:
                    parent.append(prev_obj.data)
                elif ch.level < prev_ch.level:
                    for _ in range(prev_ch.level - ch.level):
                        parent.pop()
                parent[-1][ch.title] = ch_obj
            prev_ch = ch
            prev_obj = ch_obj
        self.logger.debug(f"Group res: {res}")
        return res

    def _get_to_args(self,
                     result_data: Optional[Sequence[ResultDataEnum]] = None,
                     mode: ModeEnum = None,
                     ):
        result_data = self.result_data if result_data is None else result_data
        mode = self.mode if mode is None else mode
        return result_data, mode

    def to(self,
           format_: Literal["dict", "list"],
           result_data: Optional[Sequence[ResultDataEnum]] = None,
           mode: ModeEnum = None,
           chapters: list = None,
           chapters_nested: bool = None,
           chapters_max_level: Optional[int] = None,
           ):
        return getattr(self, f"to_{format_}")(result_data, mode, chapters, chapters_nested, chapters_max_level)

    def to_dict(self,
                result_data: Optional[Sequence[ResultDataEnum]] = None,
                mode: ModeEnum = None,
                chapters: list = None,
                chapters_nested: bool = None,
                chapters_max_level: Optional[int] = None,
                ) -> dict:
        result_data, mode = self._get_to_args(result_data, mode)
        if mode in [ModeEnum.CHAPTERS, ModeEnum.CHAPTERS_TYPE]:
            return {ch: collector.to_dict(result_data) for ch, collector in
                    self.group_by_chapters(chapters, chapters_nested, chapters_max_level, mode).items()}
        return {i: collector.to_dict(result_data) for i, collector in self.data.items()}

    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None,
                mode: ModeEnum = None,
                chapters: list = None,
                chapters_nested: bool = None,
                chapters_max_level: Optional[int] = None,
                ) -> list:
        result_data, mode = self._get_to_args(result_data, mode)
        if mode in [ModeEnum.CHAPTERS, ModeEnum.CHAPTERS_TYPE]:
            return [collector.to_list(result_data) for collector in
                    self.group_by_chapters(chapters, chapters_nested, chapters_max_level, mode).values()]
        return [collector.to_list(result_data) for collector in self.data.values()]

    def add_page(self, pno: int, page_collector: PageResultCollector):
        self.data[pno] = page_collector
