"""Weather icons drawn with Pillow primitives (no image assets)."""
import math

from PIL import ImageDraw

BLACK = 0
CLOUD_FILL = 0x88
BG = 255

Box = tuple[int, int, int, int]


def _sub(box: Box, fx0: float, fy0: float, fx1: float, fy1: float) -> Box:
    """Fractional sub-box of box."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    return (round(x0 + fx0 * w), round(y0 + fy0 * h), round(x0 + fx1 * w), round(y0 + fy1 * h))


def _sun(draw: ImageDraw.ImageDraw, box: Box, lw: int) -> None:
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    size = min(x1 - x0, y1 - y0)
    r = size * 0.22
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLACK)
    r_in, r_out = size * 0.32, size * 0.47
    for k in range(8):
        a = k * math.pi / 4
        draw.line(
            (cx + r_in * math.cos(a), cy + r_in * math.sin(a),
             cx + r_out * math.cos(a), cy + r_out * math.sin(a)),
            fill=BLACK, width=lw,
        )


def _moon(draw: ImageDraw.ImageDraw, box: Box, lw: int) -> None:
    x0, y0, x1, y1 = box
    size = min(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = size * 0.4
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLACK)
    ox, oy = cx + r * 0.55, cy - r * 0.35
    r2 = r * 0.85
    draw.ellipse((ox - r2, oy - r2, ox + r2, oy + r2), fill=BG)


def _cloud(draw: ImageDraw.ImageDraw, box: Box, lw: int) -> None:
    shapes = [
        ("e", _sub(box, 0.00, 0.45, 0.42, 1.00)),
        ("e", _sub(box, 0.18, 0.00, 0.72, 0.92)),
        ("e", _sub(box, 0.52, 0.30, 1.00, 1.00)),
        ("r", _sub(box, 0.20, 0.55, 0.78, 1.00)),
    ]
    # Union silhouette in black, then the same shapes inset by lw in gray:
    # gives a single outline without seams between the parts.
    for inset, color in ((0, BLACK), (lw, CLOUD_FILL)):
        for kind, (a, b, c, d) in shapes:
            xy = (a + inset, b + inset, c - inset, d - inset)
            if kind == "e":
                draw.ellipse(xy, fill=color)
            else:
                draw.rectangle(xy, fill=color)


def _star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, lw: int) -> None:
    for k in range(3):
        a = k * math.pi / 3 + math.pi / 2
        dx, dy = r * math.cos(a), r * math.sin(a)
        draw.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=BLACK, width=lw)


def _drop(draw: ImageDraw.ImageDraw, box: Box, fx: float, lw: int) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    draw.line((x0 + fx * w, y0 + 0.72 * h, x0 + (fx - 0.10) * w, y0 + 0.98 * h), fill=BLACK, width=lw)


def _upper_cloud(draw: ImageDraw.ImageDraw, box: Box, lw: int) -> None:
    _cloud(draw, _sub(box, 0.0, 0.02, 1.0, 0.64), lw)


def _partly(draw: ImageDraw.ImageDraw, box: Box, lw: int, night: bool) -> None:
    corner = _sub(box, 0.38, 0.0, 1.0, 0.62)
    (_moon if night else _sun)(draw, corner, lw)
    _cloud(draw, _sub(box, 0.0, 0.38, 0.82, 0.92), lw)


def draw_icon(draw: ImageDraw.ImageDraw, kind: str, box: Box) -> None:
    lw = max(1, (box[2] - box[0]) // 20)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if kind == "sun":
        _sun(draw, box, lw)
    elif kind == "moon":
        _moon(draw, box, lw)
    elif kind == "partly":
        _partly(draw, box, lw, night=False)
    elif kind == "partly_night":
        _partly(draw, box, lw, night=True)
    elif kind == "rain":
        _upper_cloud(draw, box, lw)
        for fx in (0.32, 0.52, 0.72):
            _drop(draw, box, fx, lw)
    elif kind == "snow":
        _upper_cloud(draw, box, lw)
        for fx in (0.22, 0.50, 0.78):
            _star(draw, x0 + fx * w, y0 + 0.84 * h, 0.10 * w, lw)
    elif kind == "sleet":
        _upper_cloud(draw, box, lw)
        _drop(draw, box, 0.38, lw)
        _star(draw, x0 + 0.64 * w, y0 + 0.84 * h, 0.10 * w, lw)
    elif kind == "thunder":
        _upper_cloud(draw, box, lw)
        bolt = [(0.55, 0.50), (0.38, 0.78), (0.50, 0.78), (0.42, 1.00), (0.66, 0.68), (0.53, 0.68), (0.62, 0.50)]
        draw.polygon([(x0 + fx * w, y0 + fy * h) for fx, fy in bolt], fill=BLACK)
    elif kind == "fog":
        for k, (fa, fb) in enumerate(((0.10, 0.80), (0.20, 0.90), (0.05, 0.75), (0.25, 0.95))):
            y = y0 + (0.25 + k * 0.17) * h
            draw.line((x0 + fa * w, y, x0 + fb * w, y), fill=BLACK, width=lw)
    else:
        _cloud(draw, _sub(box, 0.0, 0.15, 1.0, 0.85), lw)
