"""Draw the source-content distinction in the publication Figure 3A workflow.

This explanatory overlay changes no data or model result. Numerical expression
profiles and task context feed the original-prompt annotation path. Retrospective
marker-name-list exports have their own branch, with no arrow to the LLMs.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def draw_prompt_workflow(image: Image.Image, rect: list[int], font_path: Path) -> None:
    x, y, width, height = rect
    draw = ImageDraw.Draw(image)
    sx, sy = (width - 1) / 800, (height - 1) / 300
    def point(px: float, py: float) -> tuple[int, int]:
        return round(x + px * sx), round(y + py * sy)
    line_width = max(1, round(2 * sy))
    def text(px: float, py: float, value: str, size: int) -> None:
        font = ImageFont.truetype(str(font_path), round(size * sy))
        draw.text(point(px, py), value, font=font, fill='black', anchor='mm')
    def box(left: float, top: float, right: float, bottom: float) -> None:
        draw.rectangle((*point(left, top), *point(right, bottom)), outline='black', width=line_width)
    def arrow(points: list[tuple[float, float]]) -> None:
        draw.line([point(*p) for p in points], fill='black', width=line_width)
        end_x, end_y = points[-1]
        draw.polygon([point(end_x, end_y), point(end_x - 8, end_y - 4), point(end_x - 8, end_y + 4)], fill='black')

    text(365, 17, 'Original prompt inputs', 21)
    box(55, 50, 675, 150)
    text(365, 84, 'Numerical marker-expression profiles', 22)
    text(365, 118, 'and task context', 21)
    arrow([(0, 172), (25, 172), (25, 100), (55, 100)])
    arrow([(675, 100), (740, 100), (740, 172), (800, 172)])

    box(55, 193, 675, 284)
    text(365, 216, 'Retrospective marker-name-list exports', 20)
    text(365, 246, 'Thresholds and marker-count limits', 18)
    text(365, 271, 'Not verified as original prompt content', 17)
    arrow([(25, 172), (25, 236), (55, 236)])
