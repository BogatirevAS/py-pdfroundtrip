from enum import StrEnum, IntEnum
from pymupdf import TEXT_ALIGN_LEFT, TEXT_ALIGN_CENTER, TEXT_ALIGN_RIGHT, TEXT_ALIGN_JUSTIFY


class TextAlignH(IntEnum):
    LEFT = TEXT_ALIGN_LEFT
    CENTER = TEXT_ALIGN_CENTER
    RIGHT = TEXT_ALIGN_RIGHT
    JUSTIFY = TEXT_ALIGN_JUSTIFY


class TextAlignV(IntEnum):
    BASELINE = 0
    BOTTOM = 1
    CENTER = 2
    TOP = 3


class AutoPageMode(IntEnum):
    DISABLE = 0
    NEW = 1
    NEXT = 2


class RectType(StrEnum):
    AREA = "area"
    PAGE = "page"
