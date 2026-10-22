from collections import Counter
from typing import Optional, Sequence
from logger import LoggerMixin

from pdfroundtrip.extractor.collectors.base import AbstractCollector
from pdfroundtrip.extractor.domain.enums import CollectorTypeEnum, ResultDataEnum
from pdfroundtrip.domain.enums import JsonKey


class ChapterCollector(AbstractCollector):
    def __init__(self, chapter: str | int | None, data: dict):
        self._type = CollectorTypeEnum.CHAPTER
        self.title = None if chapter == 0 else data.pop(0)
        self.data = data

    @property
    def type(self):
        return self._type

    def _to(self, result_data: Optional[Sequence[ResultDataEnum]] = None):
        if result_data is None:
            result_data = list(ResultDataEnum)
        temp = {}
        if ResultDataEnum.TYPE in result_data:
            temp[JsonKey.TYPE] = self.type
        return temp

    def to_dict(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        temp = self._to(result_data)
        temp.update({
            JsonKey.TITLE: self.title.to_dict(result_data) if self.title is not None else None,
            JsonKey.DATA: {k: v.to_dict(result_data) for k, v in self.data.items()}
        })
        return temp

    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        temp = self._to(result_data)
        temp.update({
            JsonKey.TITLE: self.title.to_list(result_data) if self.title is not None else None,
            JsonKey.DATA: [v.to_list(result_data) for v in self.data.values()]
        })
        return temp

    def add_span(self, span: dict) -> "AbstractCollector":
        pass


class ChapterGroupCollector(LoggerMixin):
    def __init__(self, title: str | int, level: int = 1):
        self.title = title
        self.level = level
        self.data = {}

    def add(self, collector):
        self.data[len(self.data)] = collector

    def merge(self, collector: "ChapterGroupCollector"):
        for d in collector.data.values():
            self.add(d)

    @property
    def last(self):
        return self.data[list(self.data.keys())[-1]]

    def to_type(self):
        return ChapterCollector(self.title, self.data)

    def to_dict(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> dict:
        return {i: collector.to_dict(result_data) for i, collector in self.data.items()}

    def to_list(self, result_data: Optional[Sequence[ResultDataEnum]] = None) -> list:
        return [collector.to_list(result_data) for collector in self.data.values()]


def filter_duplicate_chapters(chapters: list[ChapterGroupCollector]) -> list[ChapterGroupCollector]:
    n = len(chapters)
    parents = [None] * n
    stack: list[int] = []
    for i, ch in enumerate(chapters):
        while stack and chapters[stack[-1]].level >= ch.level:
            stack.pop()
        parents[i] = stack[-1] if stack else None
        stack.append(i)

    def key(i: int) -> tuple[int | None, int, str]:
        return parents[i], chapters[i].level, chapters[i].title

    counts = Counter(key(i) for i in range(n))
    result: list[ChapterGroupCollector] = []
    for i, ch in enumerate(chapters):
        if counts[key(i)] > 1:
            result[-1].merge(ch)
        else:
            result.append(ch)
    return result
