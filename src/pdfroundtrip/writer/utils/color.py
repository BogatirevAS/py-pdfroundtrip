from abc import ABC, abstractmethod
from typing import Any, Sequence


class AbstractColorSelector(ABC):
    @abstractmethod
    def select(self, row: int, col: int) -> Any:
        pass


class ColorSelector(AbstractColorSelector):
    def __init__(self, colors: Sequence[Sequence]) -> None:
        if not isinstance(colors, Sequence):
            raise TypeError("Not a sequence")
        if len(colors) == 0:
            raise ValueError("Empty colors")
        for i, c in enumerate(colors):
            if not isinstance(c, Sequence):
                raise TypeError(f"Not a sequence by {i} index")
            elif len(c) == 0:
                raise ValueError(f"Empty colors by {i} index")
        self._colors = colors

    def select(self, row: int, col: int) -> Any:
        r = row % len(self._colors)
        c = col % len(self._colors[r])
        return self._colors[r][c]
