from dataclasses import dataclass
from typing import Any
from pymupdf import Font, Point
from rgb_tuple import RGBTuple

from pdfroundtrip.domain.enums import TextTypeEnum


@dataclass
class Style:
    size: float
    color: RGBTuple
    font: Font


@dataclass
class Span:
    text: str
    style: Style


@dataclass
class Token:
    text: str
    style: Style
    width: float
    height: float
    descender: float


@dataclass
class Paddings:
    left: float
    top: float
    right: float
    bottom: float


@dataclass
class BlockSides:
    left: Any
    top: Any
    right: Any
    bottom: Any


class BlockSidesTuple(tuple):
    def __new__(cls, *args):
        if len(args) != 4:
            raise TypeError(f'Expected 4 arguments, got {len(args)}')
        return super().__new__(cls, args)

    @classmethod
    def LEFT(cls, value):
        return BlockSidesTuple(value, 0, 0, 0)

    @classmethod
    def TOP(cls, value):
        return BlockSidesTuple(0, value, 0, 0)

    @classmethod
    def RIGHT(cls, value):
        return BlockSidesTuple(0, 0, value, 0)

    @classmethod
    def BOTTOM(cls, value):
        return BlockSidesTuple(0, 0, 0, value)


@dataclass
class ElementStats:
    type: TextTypeEnum
    start_page: int | None
    start_page_xref: int | None
    start_pos: Point | None
    end_page: int | None
    end_page_xref: int | None
    end_pos: Point | None
