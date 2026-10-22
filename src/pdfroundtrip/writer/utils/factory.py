from typing import Any, TypedDict, Union
from pymupdf import Rect
from typing import TYPE_CHECKING

from pdfroundtrip.domain.enums import JsonKey, TypeEnum
from pdfroundtrip.writer.utils.rect import CellSelector
if TYPE_CHECKING:
    from pdfroundtrip.writer.config.kwargs_settings import TextTypeKwargs


def clean_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


class GraphicDict(TypedDict, total=False):
    type: TypeEnum
    kwargs: dict


def image_factory(rect: Rect, file, **kwargs) -> GraphicDict:
    kwargs = kwargs or {}
    kwargs.update({
        "rect": rect,
        "file": file,
    })
    d = {
        JsonKey.TYPE.value: TypeEnum.IMAGE,
        JsonKey.KWARGS.value: kwargs,
    }
    return d


def line_factory(p1, p2, color: Any = None, width: float = None, **kwargs) -> GraphicDict:
    not_none_kwargs = {
        "p1": p1,
        "p2": p2,
        "color": color,
        "width": width,
    }
    not_none_kwargs = clean_dict(not_none_kwargs)
    kwargs = kwargs or {}
    kwargs.update(not_none_kwargs)
    d = {
        JsonKey.TYPE.value: TypeEnum.LINE,
        JsonKey.KWARGS.value: kwargs,
    }
    return d


def rect_factory(rect: Rect, color: Any = None, width: float = None,
                 fill: Any = None, fill_opacity: float = None, **kwargs) -> GraphicDict:
    not_none_kwargs = {
        "rect": rect,
        "color": color,
        "width": width,
        "fill": fill,
        "fill_opacity": fill_opacity,
    }
    not_none_kwargs = clean_dict(not_none_kwargs)
    kwargs = kwargs or {}
    kwargs.update(not_none_kwargs)
    d = {
        JsonKey.TYPE.value: TypeEnum.RECT,
        JsonKey.KWARGS.value: kwargs,
    }
    return d


class StyleDict(TypedDict, total=False):
    size: float
    bold: bool
    italic: bool
    font: str
    color: Any


class TextElementDict(TypedDict, total=False):
    type: TypeEnum
    texts: list[str]
    styles: list[StyleDict]
    area: Union[Rect, CellSelector]
    kwargs: "TextTypeKwargs"


def text_element_factory(
        type_: TypeEnum,
        texts: list[str],
        styles: list[StyleDict] = None,
        area: Rect | CellSelector = None,
        kwargs: "TextTypeKwargs" = None,
) -> TextElementDict:
    d = {
        JsonKey.TYPE.value: type_,
        JsonKey.AREA.value: area,
        JsonKey.TEXTS.value: texts,
        JsonKey.STYLES.value: styles,
        JsonKey.KWARGS.value: kwargs,
    }
    d = clean_dict(d)
    return d


def textbox_factory(
        texts: list[str],
        styles: list[StyleDict] = None,
        area: Rect | CellSelector = None,
        kwargs: "TextTypeKwargs" = None,
):
    return text_element_factory(type_=TypeEnum.TEXTBOX, texts=texts, styles=styles, area=area, kwargs=kwargs)


def title_factory(
        texts: list[str],
        styles: list[StyleDict] = None,
        area: Rect | CellSelector = None,
        kwargs: "TextTypeKwargs" = None,
        level: int = None,
):
    if level is not None:
        if kwargs is None:
            kwargs = {}
        kwargs["level"] = level
    return text_element_factory(type_=TypeEnum.TITLE, texts=texts, styles=styles, area=area, kwargs=kwargs)


def cell_factory(
        texts: list[str],
        styles: list[StyleDict] = None,
        area: Rect | CellSelector = None,
        kwargs: "TextTypeKwargs" = None,
):
    return text_element_factory(type_=TypeEnum.CELL, texts=texts, styles=styles, area=area, kwargs=kwargs)


class TableDict(TypedDict, total=False):
    type_: TypeEnum
    header: list[TextElementDict]
    body: list[list[TextElementDict]]
    kwargs: "TextTypeKwargs"


def table_factory(
        body: list[list[TextElementDict]],
        header: list[TextElementDict] = None,
        kwargs: "TextTypeKwargs" = None,
        header_kwargs: "TextTypeKwargs" = None,
) -> TableDict:
    kwargs = kwargs or {}
    if header_kwargs is not None:
        kwargs["header"] = header_kwargs
    if not kwargs:
        kwargs = None
    d = {
        JsonKey.TYPE.value: TypeEnum.TABLE,
        JsonKey.HEADER.value: header,
        JsonKey.BODY.value: body,
        JsonKey.KWARGS.value: kwargs,
    }
    d = clean_dict(d)
    return d


class ChapterDict(TypedDict, total=False):
    type: TypeEnum
    title: TextElementDict
    data: list[Union[TextElementDict, TableDict, GraphicDict, "ChapterDict"]]
    kwargs: "TextTypeKwargs"


def chapter_factory(
        data: list[TextElementDict | TableDict | GraphicDict | ChapterDict],
        title: TextElementDict = None,
        kwargs: "TextTypeKwargs" = None,
        new_page: bool = None,
        min_area: float = None,
        chapter_break_lines: int = None,
        level: int = None,
) -> ChapterDict:
    kwargs = kwargs or {}
    kwargs.update({
        "new_page": new_page,
        "min_area": min_area,
        "chapter_break_lines": chapter_break_lines,
        "level": level,
    })
    kwargs = clean_dict(kwargs)
    if not kwargs:
        kwargs = None
    d = {
        JsonKey.TYPE.value: TypeEnum.CHAPTER,
        JsonKey.TITLE.value: title,
        JsonKey.DATA.value: data,
        JsonKey.KWARGS.value: kwargs,
    }
    d = clean_dict(d)
    return d
