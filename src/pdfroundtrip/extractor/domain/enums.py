from enum import StrEnum

from pdfroundtrip.domain.enums import JsonKey, TypeEnum


class ResultDataEnum(StrEnum):
    TYPE = JsonKey.TYPE
    AREA = JsonKey.AREA
    TEXT = JsonKey.TEXT
    TEXTS = JsonKey.TEXTS
    SPANS = JsonKey.SPANS
    STYLES = JsonKey.STYLES


class ModeEnum(StrEnum):
    PAGES = "pages"
    CHAPTERS = "chapters"
    CHAPTERS_TYPE = "chapters_type"


class CollectorTypeEnum(StrEnum):
    TEXTBOX = TypeEnum.TEXTBOX
    TABLE = TypeEnum.TABLE
    CELL = TypeEnum.CELL
    CHAPTER = TypeEnum.CHAPTER
