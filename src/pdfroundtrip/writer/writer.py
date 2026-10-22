from pathlib import Path
from typing import Any, Literal, Unpack
from pymupdf import Font, Rect, pymupdf, Document
from logger import LoggerMixin

from pdfroundtrip.writer.config.kwargs_settings import DefaultTextTypeKwargs, TextTypeKwargs, KwargsManager, TextTypeKwargsWrapper
from pdfroundtrip.writer.core.coord_manager import CoordManager
from pdfroundtrip.writer.core.element_stats import ElementStatsCollector
from pdfroundtrip.writer.core.page_manager import PageManager
from pdfroundtrip.writer.core.style_manager import StyleManager
from pdfroundtrip.writer.domain.enums import AutoPageMode, RectType
from pdfroundtrip.writer.render.base.abc import AbstractRenderer
from pdfroundtrip.writer.render.base.graphic import GraphicRenderer
from pdfroundtrip.writer.render.base.text import TextRenderer
from pdfroundtrip.writer.render.table import TableRenderer
from pdfroundtrip.writer.render.textbox import TextboxRenderer
from pdfroundtrip.writer.domain.consts import A4
from pdfroundtrip.domain.enums import JsonKey, TypeEnum, TextTypeEnum, GraphicTypeEnum
from pdfroundtrip.utils.fonts import DocumentFonts
from pdfroundtrip.utils.utils import open_file, to_list


class PDFWriter(LoggerMixin):
    def __init__(self,
                 doc: Document = None,
                 page_size: tuple = A4,
                 margins: tuple[float, float, float, float] = (27.0, 12.0, 27.0, 12.0),
                 fonts: DocumentFonts | dict[str, Path | bytes | str | Font] | Path | str = None,
                 area_color: Any = None,
                 rects_gaps_xy: tuple[float, float] = (10.0, 10.0),
                 settings: dict[TextTypeEnum, DefaultTextTypeKwargs] = None,
                 **kwargs: Unpack[DefaultTextTypeKwargs],
                 ):
        self._doc = doc or pymupdf.open()
        self._area_color = area_color
        self._page_manager = PageManager(doc=self.doc,
                                         page_size=page_size,
                                         margins=margins, )
        self._coord_manager = CoordManager(area=self._page_manager.area, )
        self._settings = KwargsManager({RectType.AREA: self.area, RectType.PAGE: self.page_rect, },
                                       rects_gaps_xy, settings, **kwargs)
        self._style_manager = StyleManager(doc=self.doc,
                                           fonts=fonts,
                                           font_regular=self._settings.default.get_font(),
                                           font_bold=self._settings.default.get_font(True),
                                           font_italic=self._settings.default.get_font(False, True),
                                           font_bold_italic=self._settings.default.get_font(True, True),
                                           size=self._settings.default.size,
                                           color=self._settings.default.color, )
        self._text_renderer = TextRenderer(page_manager=self._page_manager,
                                           color=self._settings.default.color, )
        self._graphic_renderer = GraphicRenderer(page_manager=self._page_manager, )
        self._elements_stats = ElementStatsCollector()

    @property
    def doc(self):
        return self._doc

    def __enter__(self) -> "PDFWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.logger.debug("Close doc")
        self.doc.close()

    def save(self, path: Path, deflate=True, open_=False):
        self.logger.debug("Save doc")
        self._flush_page()
        self._page_manager.save_toc()
        if deflate:
            self.doc.subset_fonts()
            self.doc.save(path, garbage=4, clean=True, deflate=True, deflate_images=True, deflate_fonts=True)
        else:
            self.doc.save(path)
        if open_:
            self.logger.debug("Open doc")
            open_file(path)

    def _flush_page(self):
        self.logger.debug("Flush page")
        self._text_renderer.flush()
        if self._area_color is not None:
            self.add_rect(rect=self._page_manager.area, color=self._area_color)

    def _reset_page(self):
        self.logger.debug("Reset page")
        self._flush_page()
        self._coord_manager.reset()

    @property
    def page_rect(self):
        return self._page_manager.page_rect

    @property
    def area(self):
        return self._page_manager.area

    @property
    def page(self):
        return self._page_manager.page

    @property
    def index(self):
        return self._page_manager.index

    @property
    def last_index(self):
        return self._page_manager.last_index

    @property
    def next_index(self):
        return self._page_manager.next_index

    @property
    def is_end(self):
        return self._page_manager.is_end

    @property
    def is_next_out_of_index(self):
        return self._page_manager.is_next_out_of_index

    @property
    def xref(self):
        return self._page_manager.xref

    def xref_by_index(self, index: int):
        return self._page_manager.xref_by_index(index)

    def index_by_xref(self, xref: int):
        return self._page_manager.index_by_xref(xref)

    def save_index(self):
        self._page_manager.save_index()

    def load_index(self):
        self._page_manager.load_index()

    def new_page(self, index: int = -1):
        self._reset_page()
        return self._page_manager.new_page(index)

    def go_to_page(self, index: int):
        self._reset_page()
        return self._page_manager.go_to_page(index)

    def go_to_end_page(self):
        self._reset_page()
        return self._page_manager.go_to_end_page()

    def go_to_end_of_page(self):
        self._coord_manager.load_cursor(self.index)

    def go_to_end(self):
        self.go_to_end_page()
        self.go_to_end_of_page()

    def next_page(self):
        self._reset_page()
        return self._page_manager.next_page()

    def next_new_page(self):
        self._reset_page()
        return self._page_manager.next_new_page()

    @property
    def cursor(self):
        return self._coord_manager.cursor

    def ensure_space(self, needed_height: float):
        return self._coord_manager.ensure_space(needed_height)

    def advance_cursor(self, dy: float):
        self._coord_manager.advance_cursor(dy)
        self._coord_manager.save_larger_cursor(self.xref)

    def reset_cursor(self):
        return self._coord_manager.reset()

    def save_cursor(self, key: str = None):
        if isinstance(key, int):
            self.logger.warning(f"Int key reserved for page indexes")
            return
        return self._coord_manager.save_cursor(key)

    def load_cursor(self, key: int | str = None):
        if isinstance(key, int):
            key = self.xref_by_index(key)
        return self._coord_manager.load_cursor(key)

    def save_pos(self):
        self.logger.debug("Save position")
        self.save_index()
        self.save_cursor()

    def load_pos(self):
        self.logger.debug("Load position")
        self.load_index()
        self.go_to_page(self.index)
        self.load_cursor()

    def add_image(self, rect: Rect, file, **kwargs):
        self._graphic_renderer.add_image(rect, file, **kwargs)

    def add_line(self, p1, p2, color: Any = None, width: float = None, **kwargs):
        self._graphic_renderer.add_line(p1, p2, color, width, **kwargs)

    def add_rect(self, rect: Rect, color: Any = None, width: float = None,
                 fill: Any = None, fill_opacity: float = None, **kwargs):
        return self._graphic_renderer.add_rect(rect=rect, color=color, width=width,
                                               fill=fill, fill_opacity=fill_opacity, **kwargs)

    def page_break(self, auto=AutoPageMode.NEXT):
        self.logger.debug("Page break")
        if auto == AutoPageMode.NEW:
            self.next_new_page()
        elif auto == AutoPageMode.NEXT:
            self.next_page()
        else:
            self.logger.warning("Page break disabled")

    def line_break(self, lines=1, style: Literal["last", "default"] = "last",
                   size: float = None, line_height: float = None):
        self.logger.debug(f"Line break: {lines}")
        style_obj = self._style_manager.last_style if style == "last" else self._style_manager.default_style
        size = size or style_obj.size
        line_height = line_height or self._settings.default.line_height
        height = lines * line_height * size
        if self.ensure_space(height):
            self.advance_cursor(height)
        else:
            self.logger.warning("Out of space, skip")
            self._coord_manager.to_end()
        return self.cursor

    @property
    def elements_stats(self):
        return self._elements_stats.elements_stats

    def _start_render(self, renderer: AbstractRenderer, settings: TextTypeKwargsWrapper):
        self._elements_stats.new(settings.type, renderer.coord_manager.cursor)
        while True:
            status = renderer.add()
            if status is True:
                self._elements_stats.update_start(self.index, self.xref)
                continue
            renderer.flush()
            self._coord_manager.save_larger_cursor(self.xref)
            if status is False:
                if settings.auto:
                    self.page_break(settings.auto)
                    self._elements_stats.update_start(pos=renderer.coord_manager.cursor)
                    continue
                self.logger.warning("Out of space, increase area size or use auto mode")
            elif settings.break_lines and settings.auto:
                self.line_break(lines=settings.break_lines, line_height=settings.line_height)
            break
        self._elements_stats.update_end(self.index, self.xref, renderer.coord_manager.cursor)

    def _add_textbox(self,
                     type_: TextTypeEnum,
                     data: str | list | dict,
                     **kwargs: Unpack[TextTypeKwargs]):
        wrap = self._settings.get(type_, kwargs, data)
        coord = CoordManager(area=wrap.area) if not wrap.auto else self._coord_manager
        spans = self._style_manager.create_spans(data=data, font=wrap.get("font"), size=wrap.get("size"),
                                                 color=wrap.get("color"), bold=wrap.get("bold"),
                                                 italic=wrap.get("italic"), default=wrap, )
        textbox = TextboxRenderer(text_renderer=self._text_renderer,
                                  graphic_renderer=self._graphic_renderer,
                                  coord_manager=coord,
                                  spans=spans,
                                  settings=wrap, )
        self._start_render(textbox, wrap)
        return "".join([s.text for s in spans])

    def add_textbox(self,
                    data: str | list | dict,
                    **kwargs: Unpack[TextTypeKwargs]):
        self.logger.debug("Add textbox")
        self._add_textbox(TextTypeEnum.TEXTBOX, data, **kwargs)
        return self._text_renderer.pos

    def add_title(self,
                  data: str | list | dict,
                  level=1,
                  **kwargs: Unpack[TextTypeKwargs]):
        self.logger.debug("Add title")
        if level <= 0:
            raise ValueError("Level must be greater than 0")
        text = self._add_textbox(TextTypeEnum.TITLE, data, **kwargs)
        self._page_manager.add_title(level, text, self.elements_stats[self.xref][-1].start_page)
        return self._text_renderer.pos

    def add_table(self,
                  data: dict,
                  header: TextTypeKwargs = None,
                  **kwargs: Unpack[TextTypeKwargs]):
        self.logger.debug("Add table")
        header = header or {}
        twrap = self._settings.get(TextTypeEnum.TABLE, kwargs, data)
        hwrap = self._settings.get(TextTypeEnum.HEADER, kwargs, data, header, JsonKey.HEADER)
        coord = CoordManager(area=twrap.area) if not twrap.auto else self._coord_manager

        header_list = to_list(data.get(JsonKey.HEADER))
        header_spans = [
            self._style_manager.create_spans(data=h, font=hwrap.get("font"), size=hwrap.get("size"),
                                             color=hwrap.get("color"), bold=hwrap.get("bold"),
                                             italic=hwrap.get("italic"), default=hwrap, )
            for h in header_list]
        header_cell_kwargs = [h.get(JsonKey.KWARGS, {}) if isinstance(h, dict) else {} for h in header_list]
        body_list = to_list(data.get(JsonKey.BODY))
        body_spans = [
            [self._style_manager.create_spans(data=c, font=twrap.get("font"), size=twrap.get("size"),
                                              color=twrap.get("color"), bold=twrap.get("bold"),
                                              italic=twrap.get("italic"), default=twrap, )
             for c in to_list(r)] for r in body_list]
        body_cell_kwargs = [[c.get(JsonKey.KWARGS, {}) if isinstance(c, dict) else {} for c in to_list(r)] for r in body_list]

        table = TableRenderer(text_renderer=self._text_renderer,
                              graphic_renderer=self._graphic_renderer,
                              coord_manager=coord,
                              header_spans=header_spans,
                              body_spans=body_spans,
                              settings=twrap,
                              header_settings=hwrap,
                              header_cell_kwargs=header_cell_kwargs,
                              body_cell_kwargs=body_cell_kwargs,)
        self._start_render(table, twrap)
        return self._text_renderer.pos

    def add_chapter(self,
                    data: dict,
                    new_page=False,
                    min_area=0.0,
                    chapter_break_lines=1,
                    level=1,
                    **kwargs: Unpack[TextTypeKwargs]):
        self.logger.debug("Add chapter")
        chapter_kwargs = {"new_page": new_page, "chapter_break_lines": chapter_break_lines, "level": level} \
                         | data.get(JsonKey.KWARGS, {})
        new_page = chapter_kwargs.get("new_page")
        break_lines = chapter_kwargs.get("chapter_break_lines")
        level = chapter_kwargs.get("level")

        if self.elements_stats.get(self.xref):
            if new_page or (min_area and not self._coord_manager.ensure_space_by_area(min_area)):
                self.page_break(AutoPageMode.NEW)

        data_list = to_list(data.get(JsonKey.DATA, {}))
        title = data.get(JsonKey.TITLE)
        if title:
            self.add_title(title, level=level, **kwargs)
            level += 1
        for d in data_list:
            self.add(d, level=level, **kwargs)

        if break_lines:
            self.line_break(lines=break_lines)

    def add(self, data: str | list | dict, **kwargs):
        if isinstance(data, dict):
            type_ = data.get(JsonKey.TYPE)
            if not type_:
                raise ValueError("No type")
            method_ = getattr(self, f"add_{type_}", None)
            self.logger.debug(f"method: {method_}")
            if not method_:
                raise ValueError(f"No method for type \"{type_}\"")
            if type_ in GraphicTypeEnum:
                return method_(**data.get(JsonKey.KWARGS, {}))
            return method_(data, **kwargs)
        self.logger.debug(f"No type, try add {TypeEnum.TEXTBOX}")
        return self.add_textbox(data, **kwargs)
