from pathlib import Path
from typing import Optional, Sequence
from pymupdf import Document, Font, Base14_fontdict
from logger import LoggerMixin


DEFAULT_FONTS = {v: k for k, v in Base14_fontdict.items()}


def scan_font_dir(directory: Path | str, patterns=("*.ttf", "*.otf"), filter_: Sequence | set = None) -> dict[str, Path]:
    dir_path = Path(directory)
    fonts = {}
    filter_set = set(filter_) if filter_ is not None else set()
    for pattern in patterns:
        for path in dir_path.rglob(pattern):
            if not filter_set or path.stem in filter_set:
                fonts[path.stem] = path
    return fonts


class DocumentFonts(LoggerMixin):
    def __init__(self, doc: Document = None,
                 fonts: dict[str, Path | bytes | str | Font] | Path | str = None,
                 add_default_fonts=False):
        self.doc = doc
        self._cached = {}
        self._document_fonts = False if doc is None else None
        if add_default_fonts:
            self.register_all(DEFAULT_FONTS)
        if fonts:
            if not isinstance(fonts, dict):
                fonts = scan_font_dir(fonts)
            self.register_all(fonts)

    def _cache(self, name: str, font: Font):
        self.logger.debug(f"Cache {font} by \"{name}\"")
        self._cached[name] = font

    def register_all(self, fonts: dict[str, Path | bytes | str | Font]):
        for name, font in fonts.items():
            self.register(name, font)

    def register(self, name: str, font: Path | bytes | str | Font, force: bool = False) -> Optional[Font]:
        """
        Load font from file/buffer/code/object and cache it under the given name.
        """
        if not force and (name in self._cached):
            self.logger.warning(f'Font "{name}" already registered.')
            return None
        try:
            if isinstance(font, Font):
                self.logger.debug(f"Add {font} by \"{name}\"")
                font_ = font
            elif isinstance(font, Path):
                self.logger.debug(f"Try create font \"{name}\" by file path \"{font}\"")
                font_ = Font(fontfile=str(font))
            elif isinstance(font, bytes):
                self.logger.debug(f"Try create font \"{name}\" by bytes buffer")
                font_ = Font(fontbuffer=font)
            else:
                self.logger.debug(f"Try create font \"{name}\" by code \"{font}\"")
                font_ = Font(fontname=font)
        except Exception as e:
            self.logger.error("Can't create font", exc_info=True)
            return None
        self._cache(name, font_)
        return font_

    def get(self, name: str) -> Optional[Font]:
        """
        Return a pymupdf.Font object for the given font name.

        The search order:
          1. Check the cache (external or previously retrieved fonts).
          2. If not cached, scan the document for an embedded font whose
             base name matches (case‑insensitive).
          3. Return None if not found.
        """
        if name in self._cached:
            self.logger.debug(f"Return font \"{name}\" from cache: {self._cached[name]}")
            return self._cached[name]

        if self._document_fonts is None:
            self._scan_document_fonts()

        if self._document_fonts:
            if name in self._document_fonts:
                return self.register(name, self._document_fonts[name])

        self.logger.warning(f"Font \"{name}\" not found")
        return None

    def _scan_document_fonts(self):
        """
        Extract all embedded fonts from the document.
        Populates self._document_fonts with {base_name: font_buffer}.
        """
        self.logger.debug("Start scan document fonts")
        self._document_fonts = {}
        seen_xrefs = set()

        # Scan every page for font references
        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            fonts = page.get_fonts(full=True)
            for font_info in fonts:
                xref = font_info[0]  # cross‑reference number
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)

                try:
                    fontname, ext, _, buffer = self.doc.extract_font(xref)
                except Exception:
                    self.logger.warning(f"Can't extract font by xref \"{xref}\"", exc_info=True)
                    continue  # ignore corrupt fonts

                # Only keep embedded fonts (buffer not None and ext != "n/a")
                if buffer and ext != "n/a":
                    self.logger.debug(f"Found fontname: \"{fontname}\"")
                    # Remove subset prefix (e.g., "ABCDEF+")
                    base_name = fontname.split('+')[-1]
                    # Store under the cleaned name
                    self._document_fonts[base_name] = buffer


class FontMatrix:
    def __init__(self, regular: str | Font, bold: str | Font,
                 italic: str | Font, bold_italic: str | Font):
        self.regular = regular
        self.bold = bold
        self.italic = italic
        self.bold_italic = bold_italic
        self._font_matrix = {
            False: {
                False: self.regular,
                True: self.italic,
            },
            True: {
                False: self.bold,
                True: self.bold_italic,
            }
        }

    def get(self, bold=False, italic=False):
        return self._font_matrix[bold or False][italic or False]
