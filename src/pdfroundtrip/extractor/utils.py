from pymupdf import Rect, Page, Font, Point, TEXT_FONT_BOLD, TEXT_FONT_ITALIC
from logger import LoggerManager
from rgb_tuple import RGBTuple

from pdfroundtrip.domain.enums import JsonKey
from pdfroundtrip.utils.fonts import DocumentFonts


_logger = LoggerManager.get_named_logger(__name__)


# This function dynamically modifies the behavior of PyMuPDF classes.
# PyMuPDF is Copyright (C) Artifex Software, Inc. and licensed under AGPL-3.0.
# See the NOTICE file for details.
def pymupdf_deepcopy_patch():
    import inspect, pymupdf

    def _share(self, memo):
        return self

    for _name in dir(pymupdf):
        _cls = getattr(pymupdf, _name)
        if not inspect.isclass(_cls):
            continue
        if getattr(_cls, "__module__", "").startswith("pymupdf"):
            try:
                _cls.__deepcopy__ = _share
            except (TypeError, AttributeError):
                pass


def is_page_boundaries(page: Page, rect: Rect) -> bool:
    mediabox = page.mediabox
    if rect.x0 == mediabox.x0 or rect.x1 == mediabox.x1:
        return True
    return False


def is_rect_child(p: Rect, c: Rect) -> bool:
    return (p.x0 <= c.x0 <= p.x1
            and p.x0 <= c.x1 <= p.x1
            and p.y0 <= c.y0 <= p.y1
            and p.y0 <= c.y1 <= p.y1)


def sorted_rects(rects: list[Rect]) -> list[Rect]:
    return sorted(rects, key=lambda r: (r.y0, r.x0, r.y1, r.x1))


def drawing_type(drawing):
    if "items" in drawing:
        return drawing["items"][0][0]
    return drawing[0]


def nearest(lst, target):
    return min(lst, key=lambda x: abs(x-target))


def nearest_coord(lst, target):
    for i in range(len(lst) - 1):
        if lst[i] <= target < lst[i + 1]:
            return lst[i]
    return lst[-1]


def is_rect_higher(rect: Rect, relative: Rect):
    return rect.y1 < relative.y0


def is_rect_lower(rect: Rect, relative: Rect):
    return rect.y0 > relative.y1


def is_close_lines(r1: Rect, r2: Rect, tolerance=7):
    temp = abs(r1.y1 - r2.y0)
    res = r1.x0 == r2.x0 and temp <= tolerance
    _logger.debug(f"Check close lines: "
                  f"{r1.x0} == {r2.x0} and abs({r1.y1} - {r2.y0}) <= {tolerance} "
                  f"-> {r1.x0} == {r2.x0} and {temp} <= {tolerance} "
                  f"-> {res}")
    return res


def is_one_line(r1: Rect, r2: Rect, tolerance=2):
    m1 = (r1.y0 + r1.y1) / 2
    m2 = (r2.y0 + r2.y1) / 2
    temp = abs(m1 - m2)
    res = temp <= tolerance
    _logger.debug(f"Check one line: abs(({r1.y0} + {r1.y1}) / 2 - ({r2.y0} + {r2.y1}) / 2) <= {tolerance} -> {temp} <= {tolerance} -> {res}")
    return res


def is_one_word(left: Rect, right: Rect, tolerance=2):
    temp = abs(left.x1 - right.x0)
    res = temp <= tolerance
    _logger.debug(f"Check one word: abs({left.x1} - {right.x0}) <= {tolerance} -> {temp} <= {tolerance} -> {res}")
    return res


def is_next_line(prev_span: dict, span: dict, area: Rect, doc_fonts: DocumentFonts = None):
    prev_bbox = Rect(prev_span["bbox"])
    prev_text = prev_span["text"]
    prev_text_last_char = prev_text[-1]
    whitespace = 1 if prev_text_last_char != " " else 0
    bbox = Rect(span["bbox"])
    text = span["text"]
    first_word = text.split()[0]
    _logger.debug(f'whitespace: {whitespace}, prav_text: "{prev_text}", prev_text_last_char: "{prev_text_last_char}"')
    if doc_fonts:
        font = doc_fonts.get(span["font"])
        first_word_width = font.text_length(f"{' ' * whitespace}{first_word}", fontsize=span["size"])
    else:
        text_width = bbox.width
        first_word_width = (len(first_word) + whitespace) / len(text) * text_width
    span_x1 = prev_bbox.x1 + first_word_width
    area_x1 = area.x1 - (bbox.x0 - area.x0)
    res = span_x1 <= area_x1
    _logger.debug(f"Check next line: first_word=\"{first_word}\", "
                  f"({prev_bbox.x1} + {first_word_width}) <= {area_x1} -> {span_x1} <= {area_x1} -> {res}")
    return res


def is_list_item(text: str):
    return text in ['•', '-', '*']


def is_bold(span: dict):
    return bool(span["flags"] & TEXT_FONT_BOLD)


def is_italic(span: dict):
    return bool(span["flags"] & TEXT_FONT_ITALIC)


def is_title(span: dict):
    return is_bold(span) and span["color"] == 0


def is_subtitle(span: dict):
    return is_title(span) and span["text"].strip()[-1] == ":"


def extract_span_styles(span: dict):
    return {
        JsonKey.SIZE: span["size"],
        JsonKey.BOLD: is_bold(span),
        JsonKey.ITALIC: is_italic(span),
        JsonKey.FONT: span["font"],
        JsonKey.COLOR: RGBTuple(span["color"]).float_tuple,
    }


def find_label_point(text: str,
                     drawing_rect: Rect,
                     page_rect: Rect = Rect(0, 0, 595, 842),
                     fontsize=14, fontname="helv"):
    font = Font(fontname)
    text_width = font.text_length(text, fontsize=fontsize)
    asc = font.ascender  # Distance from baseline to top (positive)
    dsc = font.descender  # Distance from baseline to bottom (negative)
    # Total height of the glyphs
    text_height = (asc - dsc) * fontsize
    if drawing_rect.width == 0:
        # vertical line
        x = drawing_rect.x0 + fontsize / 2 \
            if drawing_rect.x0 < (page_rect.x0 + page_rect.x1) / 2 else \
            drawing_rect.x0 - (text_width + fontsize / 2)
        y = drawing_rect.y0 + (drawing_rect.height + text_height) / 2 + dsc * fontsize
    elif drawing_rect.height == 0:
        # horizontal line
        x = drawing_rect.x0 + (drawing_rect.width - text_width) / 2
        y = drawing_rect.y0 + text_height / 2 - dsc * fontsize \
            if drawing_rect.y0 < (page_rect.y0 + page_rect.y1) / 2 else \
            drawing_rect.y0 - text_height / 2 - dsc * fontsize
    else:
        # rect
        x = drawing_rect.x0 + (drawing_rect.width - text_width) / 2
        y = drawing_rect.y0 + (drawing_rect.height + text_height) / 2 + dsc * fontsize
    return Point(x, y)
