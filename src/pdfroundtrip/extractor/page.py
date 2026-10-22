from itertools import cycle
from typing import Sequence, Optional
from pymupdf import Page, Rect, Point
from logger import LoggerMixin
from rgb_tuple import RGBTuple, RGBTupleFormat

from pdfroundtrip.extractor.collectors import PageResultCollector
from pdfroundtrip.extractor.utils import sorted_rects, drawing_type, is_page_boundaries, is_rect_child, find_label_point
from pdfroundtrip.utils.fonts import DocumentFonts


class PageExtractorDebug(LoggerMixin):
    def __init__(self, drawings, cluster_drawings, table_areas, data):
        self._drawings = drawings
        self._cluster_drawings = cluster_drawings
        self._table_areas = table_areas
        self._data = data

    @property
    def drawings(self):
        return self._drawings

    @property
    def cluster_drawings(self):
        return self._cluster_drawings

    @property
    def table_areas(self):
        return self._table_areas

    @property
    def data(self):
        return self._data

    def draw(self, page: Page,
             cluster_drawings=True,
             drawings=True, drawing_types: Optional[Sequence[str]] = ("l", "re"),
             table_areas=True):
        PageDrawer(page).debug_drawing(
            cluster_drawings=self.cluster_drawings if cluster_drawings else None,
            drawings=self.drawings if drawings else None,
            table_areas=self.table_areas if table_areas else None,
            drawing_types=drawing_types,
        )


class PageExtractor(LoggerMixin):
    def __init__(self, page: Page,
                 doc_fonts: DocumentFonts = None,
                 special_separators: list[str] = None):
        self.doc_fonts = doc_fonts
        self.special_separators = special_separators
        self.page = page
        self._debug: Optional[PageExtractorDebug] = None

    @property
    def debug(self):
        return self._debug

    def find_image_rects(self):
        img_rects = []
        images = self.page.get_image_info()
        for image in images:
            img_rects.append(Rect(image["bbox"]))
        return sorted_rects(img_rects)

    def find_table_drawings(self,
                            drawing_types: Optional[Sequence[str]] = ("l", "re"),
                            cluster_drawings_min_dimension: Optional[float] = 10,
                            exclude_images=True,
                            exclude_page_boundaries=True,
                            ):
        drawings = self.page.get_drawings()
        exclude_image_rects = []
        if exclude_images:
            exclude_image_rects = self.find_image_rects()
            self.logger.debug(f"Exclude image rects: {exclude_image_rects}")

        new_drawings = []
        excluded_drawings = []
        for drawing in drawings:
            rect = drawing["rect"]
            excluded = False
            if (drawing_types is not None) and ((type_ := drawing_type(drawing)) not in drawing_types):
                excluded_drawings.append(drawing)
                self.logger.debug(f"Exclude drawing by type {type_}: {drawing}")
                continue
            if exclude_page_boundaries and is_page_boundaries(self.page, rect):
                excluded_drawings.append(drawing)
                self.logger.debug(f"Exclude drawing by page boundaries {rect}: {drawing}")
                continue
            if exclude_image_rects:
                for image_rect in exclude_image_rects:
                    if is_rect_child(image_rect, rect) or image_rect.intersects(rect):
                        excluded_drawings.append(drawing)
                        self.logger.debug(f"Exclude drawing by image rect {image_rect}: {drawing}")
                        excluded = True
                        break
                if excluded:
                    continue
            new_drawings.append(drawing)

        if cluster_drawings_min_dimension is not None:
            exclude_cluster_drawings = list(
                filter(
                    lambda r: r.width < cluster_drawings_min_dimension or r.height < cluster_drawings_min_dimension,
                    self.page.cluster_drawings(drawings=new_drawings)
                )
            )
            self.logger.debug(f"Exclude cluster drawings: {exclude_cluster_drawings}")
            if exclude_cluster_drawings:
                temp = new_drawings
                new_drawings = []
                for drawing in temp:
                    rect = drawing["rect"]
                    excluded = False
                    for cluster_rect in exclude_cluster_drawings:
                        if is_rect_child(cluster_rect, rect) or cluster_rect.intersects(rect):
                            excluded_drawings.append(drawing)
                            self.logger.debug(f"Exclude drawing by cluster drawings {cluster_rect}: {drawing}")
                            excluded = True
                            break
                    if excluded:
                        continue

        cluster_drawings = self.page.cluster_drawings(drawings=new_drawings)
        self.logger.debug(f"cluster_drawings: {cluster_drawings}")
        self.logger.debug(f"drawings: {len(drawings)} - {len(excluded_drawings)} = {len(new_drawings)}, "
                          f"tables: {len(cluster_drawings)}")

        self.logger.debug(f"excluded_drawings: {excluded_drawings}")

        return {
            "drawings": new_drawings,
            "cluster_drawings": cluster_drawings,
        }

    def find_table_areas(self, drawings, cluster_drawings=None, line_tolerance=5, delete_one_cell_table=True) -> dict:
        if cluster_drawings is None:
            cluster_drawings = self.page.cluster_drawings(drawings=drawings)
        if not cluster_drawings:
            self.logger.debug("No cluster drawings")
            return {}
        table_i = 0
        table_rect = cluster_drawings[table_i]
        table_points = {}
        self.logger.debug(f"table_i: {table_i}, table_rect: {table_rect}")
        for drawing in drawings:
            while table_i < len(cluster_drawings):
                drw_rect = drawing["rect"]
                self.logger.debug(f"table_i: {table_i}, drw_rect:   {drw_rect}")
                if is_rect_child(table_rect, drw_rect):
                    page_res = table_points.get(table_i, {"area": table_rect, "x": set(), "y": set()})
                    page_res["x"].update([drw_rect.x0, drw_rect.x1])
                    page_res["y"].update([drw_rect.y0, drw_rect.y1])
                    table_points[table_i] = page_res
                    break
                else:
                    table_i += 1
                    table_rect = cluster_drawings[table_i]
                    self.logger.debug(f"table_i: {table_i}, table_rect: {table_rect}")
        self.logger.debug(f"table_points before: {table_points}")
        delete_one_cell_table_indexes = []
        for i, table in table_points.items():
            self.logger.debug(f"table i: {i}")
            for index in ["x", "y"]:
                self.logger.debug(f"index: {index}")
                coords = sorted(table[index])
                self.logger.debug(f"points: {coords}")
                first = coords[0]
                last = coords[-1]
                temp = []
                range_ = [first]
                for v in coords[1:]:
                    self.logger.debug(f"v: {v}")
                    if abs(v - range_[-1]) > line_tolerance:
                        mid_range = (range_[0] + range_[-1]) / 2
                        self.logger.debug(f"mid_range: {range_} = {mid_range}")
                        temp.append(mid_range)
                        range_ = [v]
                    else:
                        range_.append(v)
                temp.append(last)
                temp[0] = first
                self.logger.debug(f"temp: {temp}")
                table[index] = temp
            if delete_one_cell_table and len(table["x"]) <= 2 and len(table["y"]) <= 2:
                delete_one_cell_table_indexes.append(i)
        for delete_index in delete_one_cell_table_indexes:
            self.logger.debug(f"Delete one cell table: {table_points.pop(delete_index)}")
        self.logger.debug(f"table_points after: {table_points}")
        return table_points

    def fill_data(self, page_data: dict, table_areas: dict):
        return PageResultCollector(table_areas,
                                   self.page.mediabox,
                                   self.doc_fonts,
                                   self.special_separators).fill_data(page_data)

    def extract(self,
                page_data: dict,
                drawing_types: Optional[Sequence[str]] = ("l", "re"),
                cluster_drawings_min_dimension: Optional[float] = 10,
                exclude_images=True,
                exclude_page_boundaries=True,
                line_tolerance=5,
                delete_one_cell_table=True,
                ):
        drawings, cluster_drawings = self.find_table_drawings(
            drawing_types=drawing_types,
            cluster_drawings_min_dimension=cluster_drawings_min_dimension,
            exclude_images=exclude_images,
            exclude_page_boundaries=exclude_page_boundaries,
        ).values()
        table_areas = self.find_table_areas(
            drawings=drawings,
            cluster_drawings=cluster_drawings,
            line_tolerance=line_tolerance,
            delete_one_cell_table=delete_one_cell_table,
        )
        res = self.fill_data(page_data, table_areas)
        self._debug = PageExtractorDebug(drawings, cluster_drawings, table_areas, res)
        return res


class PageDrawer(LoggerMixin):
    class DrawerRGBTuple(RGBTuple):
        format = RGBTupleFormat.FLOAT_TUPLE

    rgb = DrawerRGBTuple

    def __init__(self, page: Page):
        self.page = page
        self.rgb.init_default_colors()

    def get_tables_lines(self, table_points):
        lines = set()
        for points in table_points.values():
            xl = points["x"]
            yl = points["y"]
            lines.update([(Point(x, yl[0]), Point(x, yl[-1])) for x in xl])
            lines.update([(Point(xl[0], y), Point(xl[-1], y)) for y in yl])
        # First, the horizontal lines
        lines = sorted(lines, key=lambda l: (l[1].y - l[0].y, l[0].y, l[0].x))
        return lines

    def draw_lines(self, lines):
        for p0, p1 in lines:
            self.page.draw_line(p0, p1, color=self.rgb.RED, width=3, dashes="[9 18] 0")

    def draw_drawings(self, drawings,
                      types: Optional[Sequence[str]] = ("l", "re"),
                      colors: list[RGBTuple] = None,
                      add_labels=True):
        if colors is None:
            colors = [
                self.rgb.DARK_ORANGE,
                self.rgb.DEEP_SKY_BLUE,
                self.rgb.ORANGE,
                self.rgb.DODGER_BLUE,
                self.rgb.GOLD,
                self.rgb.BLUE,
                self.rgb.YELLOW,
                self.rgb.DARK_VIOLET,
                self.rgb.DARK_GREEN,
                self.rgb.PURPLE,
                self.rgb.GREEN,
                self.rgb.DARK_MAGENTA,
                self.rgb.LIME,
                self.rgb.MAGENTA,
                self.rgb.SPRING_GREEN,
                self.rgb.VIOLET,
                self.rgb.AQUA_MARINE,
                self.rgb.DEEP_PINK,
                self.rgb.TURQUOISE,
                self.rgb.CRIMSON,
                self.rgb.CYAN,
            ]
        else:
            colors = [self.rgb(c).float_tuple for c in colors]

        color_cycler = cycle(colors)
        for i, drawing in enumerate(drawings):
            for item in drawing["items"]:
                color = next(color_cycler)
                type_ = drawing_type(drawing)
                if type_ not in types:
                    continue
                points: tuple[Point] = item[1:]
                if type_ == "l":  # Line
                    self.page.draw_line(points[0], points[1], color=color, width=2)
                elif type_ == "re":  # Rectangle
                    self.page.draw_rect(drawing.get("rect"), color=color, fill=color, fill_opacity=0.5, width=0)

                # Add label with object number and color index
                if add_labels:
                    temp_points = []
                    for p in points:
                        if isinstance(p, Point):
                            temp_points.append(f"({round(p.x)},{round(p.y)})")
                        elif isinstance(p, Rect):
                            temp_points = f"({round(p.x0)},{round(p.y0)}), ({round(p.x1)},{round(p.y1)})"
                    if isinstance(temp_points, list):
                        temp_points = ", ".join(temp_points)
                    points_text = temp_points
                    label = f"{i}({type_}, {points_text})"
                    label_pos = find_label_point(label, drawing.get("rect"), fontsize=12)

                    # Draw label with contrasting background
                    self.page.insert_text(
                        point=label_pos,
                        text=label,
                        fontsize=12,
                        color=self.rgb.BLACK,
                        fill=color,
                        render_mode=2,
                        border_width=0.001,
                    )

    def draw_rects(self, rects: list[Rect]):
        for rect in rects:
            self.page.draw_rect(
                rect,
                color=self.rgb.BLACK,
                width=10.0,
            )

    def debug_drawing(self, cluster_drawings, drawings, table_areas,
                      drawing_types: Optional[Sequence[str]] = ("l", "re")):
        if cluster_drawings:
            self.draw_rects(cluster_drawings)
        if drawings:
            self.draw_drawings(drawings, drawing_types)
        if table_areas:
            lines = self.get_tables_lines(table_areas)
            self.draw_lines(lines)
