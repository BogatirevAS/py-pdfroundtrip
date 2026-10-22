import re
from pymupdf import Rect

from pdfroundtrip.writer.domain.models import Span, Token, Style


def split_span_text(span: Span):
    tokens = re.split(r'(\s+)', span.text)
    for i in (-1, 0):
        if tokens[i] == "":
            tokens.pop(i)
    return tokens


def create_token(text: str, style: Style):
    return Token(
        text,
        style,
        style.font.text_length(text, fontsize=style.size),
        (style.font.ascender - style.font.descender) * style.size,
        -style.font.descender * style.size,
    )


def break_lines(spans: list[Span], max_width: float | None, merge=True) -> list[list[Token]]:
    lines = []
    line = []
    lines.append(line)
    line_width = 0.0
    for span in spans:
        tokens = split_span_text(span)
        for token in tokens:
            new_line = False
            t = create_token(token, span.style)
            if max_width is None or (line_width + t.width <= max_width):
                if merge and (line_width > 0) and (t.style == line[-1].style):
                    line[-1] = create_token(line[-1].text + t.text, span.style)
                else:
                    line.append(t)
                line_width += t.width
            elif t.text != " ":
                line = [t]
                lines.append(line)
                line_width = t.width
            else:
                new_line = True
            if t.text.endswith("\n"):
                new_line = True
            if new_line:
                line = []
                lines.append(line)
                line_width = 0.0
    return lines


def break_row_lines(spans: list[list[Span]], col_rects: list[Rect]) -> \
        list[dict[int, list[Token]]]:
    rows = {}
    for coln, cell in enumerate(spans):
        cr = col_rects[coln]
        lines = break_lines(cell, cr.width)
        for rown, l in enumerate(lines):
            r = rows.get(rown)
            if r is None:
                r = {}
                rows[rown] = r
            r[coln] = l
    return list(rows.values())


def calc_line_sizes(tokens: list[Token], line_height: float) -> tuple[float, float, float, float]:
    max_height = 0.0
    total_width = 0.0
    max_desc = 0.0
    max_size = 0.0
    for token in tokens:
        h = token.height
        if h > max_height:
            max_height = h
        d = token.descender
        if d > max_desc:
            max_desc = d
        s = token.style.size * line_height
        if s > max_size:
            max_size = s
        total_width += token.width
    return max_height, total_width, max_desc, max_size


def calc_rol_line_sizes(tokens: dict[int, list[Token]], line_height: float) -> tuple[float, dict[int, float], float, float]:
    max_height = 0.0
    widths = {}
    max_desc = 0.0
    max_size = 0.0
    for i, token in tokens.items():
        h, w, d, s = calc_line_sizes(token, line_height)
        if h > max_height:
            max_height = h
        if d > max_desc:
            max_desc = d
        if s > max_size:
            max_size = s
        widths[i] = w
    return max_height, widths, max_desc, max_size
