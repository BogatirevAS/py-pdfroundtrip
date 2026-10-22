from abc import ABC, abstractmethod
from typing import Protocol, Any
from pymupdf import Rect
from logger import LoggerMixin

from pdfroundtrip.writer.core.coord_manager import CoordManager
from pdfroundtrip.writer.domain.enums import TextAlignH, TextAlignV
from pdfroundtrip.writer.domain.models import Paddings, BlockSides


class SettingsProtocol(Protocol):
    @property
    def area(self) -> Rect:
        pass

    @property
    def align_horiz(self) -> TextAlignH:
        pass

    @property
    def align_vert(self) -> TextAlignV:
        pass

    @property
    def line_height(self) -> float:
        pass

    @property
    def paddings(self) -> Paddings:
        pass

    @property
    def line_width(self) -> BlockSides:
        pass

    @property
    def line_color(self) -> BlockSides:
        pass

    @property
    def fill_color(self) -> Any:
        pass

    def get_fill_color(self, row=0, col=0) -> Any:
        pass

    @property
    def fill_opacity(self) -> float:
        pass

    @property
    def split_lines(self) -> bool:
        pass


class AbstractRenderer(LoggerMixin, ABC):
    def __init__(self, lines: list, coord_manager: CoordManager, settings: SettingsProtocol):
        self.lines = lines
        self.coord_manager = coord_manager
        self.settings = settings

    @property
    def line(self):
        if self.lines:
            return self.lines[0]
        return None

    def pop(self):
        self.logger.debug("Pop line")
        return self.lines.pop(0)

    @abstractmethod
    def add(self) -> bool | None:
        pass

    @abstractmethod
    def flush(self):
        pass
