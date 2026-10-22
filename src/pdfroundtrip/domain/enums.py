from enum import Enum, StrEnum


class TypeEnum(StrEnum):
    TEXTBOX = "textbox"
    TITLE = "title"
    TABLE = "table"
    CELL = "cell"
    CHAPTER = "chapter"
    LINE = "line"
    RECT = "rect"
    IMAGE = "image"


class TextTypeEnum(StrEnum):
    TEXTBOX = TypeEnum.TEXTBOX
    TITLE = TypeEnum.TITLE
    TABLE = TypeEnum.TABLE
    HEADER = "header"


class GraphicTypeEnum(StrEnum):
    LINE = TypeEnum.LINE
    RECT = TypeEnum.RECT
    IMAGE = TypeEnum.IMAGE


class JsonKey(StrEnum):
    TYPE = "type"
    AREA = "area"
    TEXT = "text"
    TEXTS = "texts"
    SPANS = "spans"
    STYLES = "styles"
    FONT = "font"
    SIZE = "size"
    COLOR = "color"
    BOLD = "bold"
    ITALIC = "italic"
    HEADER = "header"
    BODY = "body"
    TITLE = "title"
    DATA = "data"
    KWARGS = "kwargs"


class StyleSwitch(Enum):
    ENABLE = 0
    DISABLE = 1


class FontEnum(StrEnum):
    HELVETICA_REGULAR = "Helvetica"
    HELVETICA_BOLD = "Helvetica-Bold"
    HELVETICA_ITALIC = "Helvetica-Oblique"
    HELVETICA_BOLD_ITALIC = "Helvetica-BoldOblique"
    LIBERATION_SERIF_REGULAR = "LiberationSerif-Regular"
    LIBERATION_SERIF_BOLD = "LiberationSerif-Bold"
    LIBERATION_SERIF_ITALIC = "LiberationSerif-Italic"
    LIBERATION_SERIF_BOLD_ITALIC = "LiberationSerif-BoldItalic"
    NOTO_SANS_REGULAR = "NotoSans-Regular"
    NOTO_SANS_BOLD = "NotoSans-Bold"
    NOTO_SANS_ITALIC = "NotoSans-Italic"
    NOTO_SANS_BOLD_ITALIC = "NotoSans-BoldItalic"
    ROBOTO_REGULAR = "Roboto-Regular"
    ROBOTO_BOLD = "Roboto-Bold"
    ROBOTO_ITALIC = "Roboto-Italic"
    ROBOTO_BOLD_ITALIC = "Roboto-BoldItalic"
