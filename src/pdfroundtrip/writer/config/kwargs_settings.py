from types import NoneType
from typing import Any, TypedDict, Unpack, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymupdf import Rect
from logger import SettingsCreateOrUpdateMixin, LoggerMixin

from pdfroundtrip.writer.domain.enums import TextAlignH, TextAlignV, AutoPageMode, RectType
from pdfroundtrip.writer.domain.models import Paddings, BlockSides
from pdfroundtrip.writer.utils.color import AbstractColorSelector
from pdfroundtrip.writer.utils.rect import CellSelector
from pdfroundtrip.domain.enums import StyleSwitch, FontEnum, TextTypeEnum, JsonKey
from pdfroundtrip.utils.fonts import FontMatrix
from pdfroundtrip.utils.json import get_json_param


class DefaultTextTypeKwargs(TypedDict, total=False):
    area: Union[Rect, CellSelector]
    align_horiz: TextAlignH
    align_vert: TextAlignV
    line_height: float
    font: str | FontMatrix
    size: float
    color: Any
    bold: bool
    italic: bool
    paddings: float | tuple[float, float, float, float]
    line_width: float | tuple[float, float, float, float]
    line_color: Any | tuple[Any, Any, Any, Any]
    fill_color: Any | AbstractColorSelector
    fill_opacity: float
    split_lines: bool
    break_lines: int
    auto: AutoPageMode


class DefaultTextTypeKwargsSettings(BaseSettings, SettingsCreateOrUpdateMixin):
    model_config = SettingsConfigDict(extra="ignore")

    type: TextTypeEnum | None = None
    area: Rect
    align_horiz: TextAlignH = TextAlignH.LEFT
    align_vert: TextAlignV = TextAlignV.BASELINE
    line_height: float = 1.2
    font: str | FontMatrix = FontMatrix(FontEnum.HELVETICA_REGULAR,
                                        FontEnum.HELVETICA_BOLD,
                                        FontEnum.HELVETICA_ITALIC,
                                        FontEnum.HELVETICA_BOLD_ITALIC)
    size: float = 12
    color: Any = (0, 0, 0)
    bold: bool = False
    italic: bool = False
    paddings: float | tuple[float, float, float, float] = (5.0, 5.0, 5.0, 5.0)
    line_width: float | tuple[float, float, float, float] = 1.0
    line_color: Any | tuple[Any, Any, Any, Any] = (0, 0, 0)
    fill_color: Any | AbstractColorSelector = None
    fill_opacity: float = 1
    split_lines: bool = True
    break_lines: int = 1
    auto: AutoPageMode = AutoPageMode.NEXT

    def get_font(self, bold=False, italic=False):
        if isinstance(self.font, FontMatrix):
            return self.font.get(bold=bold, italic=italic)
        return self.font

    def get_fill_color(self, row: int, col: int):
        if isinstance(self.fill_color, AbstractColorSelector):
            return self.fill_color.select(row, col)
        return self.fill_color


class TextTypeKwargs(TypedDict, total=False):
    area: Union[Rect, CellSelector, StyleSwitch, NoneType]
    align_horiz: TextAlignH | None
    align_vert: TextAlignV | None
    line_height: float | None
    font: str | FontMatrix | StyleSwitch | None
    size: float | StyleSwitch | None
    color: Any | StyleSwitch | None
    bold: bool | StyleSwitch | None
    italic: bool | StyleSwitch | None
    paddings: float | tuple[float, float, float, float] | None
    line_width: float | tuple[float, float, float, float] | None
    line_color: Any | tuple[Any, Any, Any, Any] | None
    fill_color: Any | AbstractColorSelector | None
    fill_opacity: float | None
    split_lines: bool | None
    break_lines: int | None
    auto: AutoPageMode | None


class TextTypeKwargsWrapper:
    def __init__(self, default: DefaultTextTypeKwargsSettings, kwargs: TextTypeKwargs,
                 rects: dict[RectType, Rect], rects_gaps_xy: tuple[float, float], ):
        self._default = default
        self._kwargs = kwargs
        self._rects = rects
        self._rects_gaps_xy = rects_gaps_xy
        self._cache = {}

    def get(self, key: str):
        return self._kwargs.get(key)

    def _get_attr(self, name: str) -> Any:
        attr = self._kwargs.get(name, None)
        if isinstance(attr, (NoneType, StyleSwitch)):
            attr = self._default.__getattribute__(name)
        return attr

    @property
    def type(self):
        return self._default.type

    @property
    def area(self):
        if not self._cache.get("area"):
            rect = self._get_attr("area")
            if isinstance(rect, CellSelector):
                rect = rect.select(self._rects, *self._rects_gaps_xy)
            self._cache["area"] = rect
        return self._cache["area"]

    @property
    def align_horiz(self) -> TextAlignH:
        return self._get_attr("align_horiz")

    @property
    def align_vert(self) -> TextAlignV:
        return self._get_attr("align_vert")

    @property
    def line_height(self) -> float:
        return self._get_attr("line_height")

    @property
    def font(self) -> str | FontMatrix:
        return self._get_attr("font")

    def get_font(self, bold=False, italic=False) -> str:
        font = self._get_attr("font")
        if isinstance(font, FontMatrix):
            return font.get(bold=bold, italic=italic)
        return font

    @property
    def size(self) -> float:
        return self._get_attr("size")

    @property
    def color(self) -> Any:
        return self._get_attr("color")

    @property
    def bold(self) -> bool:
        return self._get_attr("bold")

    @property
    def italic(self) -> bool:
        return self._get_attr("italic")

    @property
    def paddings(self) -> Paddings:
        if not self._cache.get("paddings"):
            paddings = self._get_attr("paddings")
            if isinstance(paddings, tuple):
                self._cache["paddings"] = Paddings(*paddings)
            else:
                self._cache["paddings"] = Paddings(*[paddings]*4)
        return self._cache["paddings"]

    @property
    def line_width(self) -> BlockSides:
        if self._cache.get("line_width") is None:
            line_width = self._get_attr("line_width")
            if isinstance(line_width, tuple):
                self._cache["line_width"] = BlockSides(*line_width)
            else:
                self._cache["line_width"] = BlockSides(*[line_width]*4)
        return self._cache["line_width"]

    @property
    def line_color(self) -> BlockSides:
        if self._cache.get("line_color") is None:
            line_color = self._get_attr("line_color")
            if isinstance(line_color, tuple) and len(line_color) == 4:
                self._cache["line_color"] = BlockSides(*line_color)
            else:
                self._cache["line_color"] = BlockSides(*[line_color]*4)
        return self._cache["line_color"]

    @property
    def fill_color(self) -> Any:
        return self._get_attr("fill_color")

    def get_fill_color(self, row=0, col=0) -> Any:
        fill_color = self._get_attr("fill_color")
        if isinstance(fill_color, AbstractColorSelector):
            return fill_color.select(row, col)
        return fill_color

    @property
    def fill_opacity(self) -> float:
        return self._get_attr("fill_opacity")

    @property
    def split_lines(self) -> bool:
        return self._get_attr("split_lines")

    @property
    def break_lines(self) -> int:
        return self._get_attr("break_lines")

    @property
    def auto(self) -> AutoPageMode:
        return self._get_attr("auto")


class KwargsManager(LoggerMixin):
    def __init__(self,
                 rects: dict[RectType, Rect],
                 rects_gaps_xy: tuple[float, float],
                 settings: dict[TextTypeEnum, DefaultTextTypeKwargs] = None,
                 **kwargs: Unpack[DefaultTextTypeKwargs], ):
        self._rects = rects
        self._rects_gaps_xy = rects_gaps_xy
        self._set_default_area(kwargs, self._rects.get(RectType.AREA))
        self._default = DefaultTextTypeKwargsSettings(**kwargs)
        self._types = {}
        settings = settings or {}
        temp_kwargs = DefaultTextTypeKwargs(paddings=(0, 0, 0, 0),
                                            line_width=0, ) \
                      | settings.get(TextTypeEnum.TEXTBOX, {}) \
                      | {"type": TextTypeEnum.TEXTBOX}
        self._set_default_area(temp_kwargs, self._default.area)
        self._types[TextTypeEnum.TEXTBOX] = self._default.create_or_update(self._default,
                                                                           **temp_kwargs)
        temp_kwargs = DefaultTextTypeKwargs(align_horiz=TextAlignH.CENTER,
                                            size=self._types[TextTypeEnum.TEXTBOX].size + 2,
                                            bold=True,
                                            split_lines=False,
                                            break_lines=2, ) \
                      | settings.get(TextTypeEnum.TITLE, {}) \
                      | {"type": TextTypeEnum.TITLE}
        self._set_default_area(temp_kwargs, self._types[TextTypeEnum.TEXTBOX].area)
        self._types[TextTypeEnum.TITLE] = self._default.create_or_update(
            self._types[TextTypeEnum.TEXTBOX], **temp_kwargs)
        temp_kwargs = DefaultTextTypeKwargs(align_vert=TextAlignV.CENTER) \
                      | settings.get(TextTypeEnum.TABLE, {}) \
                      | {"type": TextTypeEnum.TABLE}
        self._set_default_area(temp_kwargs, self._default.area)
        self._types[TextTypeEnum.TABLE] = self._default.create_or_update(self._default,
                                                                         **temp_kwargs)
        temp_kwargs = DefaultTextTypeKwargs(align_horiz=TextAlignH.CENTER,
                                            bold=True, ) \
                      | settings.get(TextTypeEnum.HEADER, {}) \
                      | {"type": TextTypeEnum.HEADER}
        self._set_default_area(temp_kwargs, self._types[TextTypeEnum.TABLE].area)
        self._types[TextTypeEnum.HEADER] = self._default.create_or_update(
            self._types[TextTypeEnum.TABLE], **temp_kwargs)

    def _set_default_area(self, kwargs: DefaultTextTypeKwargs, default: Rect):
        rect = kwargs.get("area")
        if isinstance(rect, CellSelector):
            rect = rect.select(self._rects, *self._rects_gaps_xy)
        rect = rect or default
        kwargs["area"] = rect

    @property
    def default(self):
        return self._default

    def get(self, type_: TextTypeEnum, kwargs: TextTypeKwargs = None, data: str | list | dict = None,
            subkwargs: TextTypeKwargs = None, subkey: JsonKey = None):
        kwargs = kwargs or {}
        subkwargs = subkwargs or {}
        kwargs = kwargs | subkwargs
        if isinstance(data, dict):
            data_kwargs = data.get(JsonKey.KWARGS, {})
            kwargs = kwargs | data_kwargs
            if subkey is not None:
                kwargs = kwargs | data_kwargs.get(subkey, {})
            kwargs["area"] = get_json_param(JsonKey.AREA, data, kwargs.get(JsonKey.AREA, None))
        self.logger.debug(f"Merged kwargs: {kwargs}")
        return TextTypeKwargsWrapper(self._types[type_], kwargs, self._rects, self._rects_gaps_xy)
