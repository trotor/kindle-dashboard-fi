"""Kuvakaappaukset README:hen / README screenshots.

    uv run python scripts/make_screenshots.py

Piirtää esimerkkidatasta (tests/sample_state.py) kuvat kansioon docs/images.
Renders the sample data into docs/images.
"""
import sys
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from saasahko.prices import cheapest_hours  # noqa: E402
from saasahko.render import render  # noqa: E402
from tests.sample_state import sample_state  # noqa: E402

# Kylmä arkipäivä: aamu- ja iltapiikki yli kipurajan / a cold weekday with two peaks over the limit
TOMORROW = [
    1.8, 1.5, 1.3, -1.2, 1.2, 1.4, 6.9, 18.4, 26.3, 21.7, 12.8, 9.2,
    8.1, 7.6, 9.4, 13.8, 22.1, 31.5, 34.2, 24.0, 11.1, 6.8, 4.6, 3.2,
]


def demo(**kw):
    return sample_state(
        prices_tomorrow=list(TOMORROW), cheapest_tomorrow=cheapest_hours(TOMORROW), price_limit=15.0, **kw
    )

OUT = ROOT / "docs" / "images"
FONTS = "/System/Library/Fonts/Supplemental/"
PAPER = (236, 235, 228)  # e-ink paper tone
BEZEL = (28, 28, 30)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONTS + ("Arial Bold.ttf" if bold else "Arial.ttf"), size)


def error_banner(img: Image.Image, text: str) -> Image.Image:
    """Same place as the Kindle draws it with fbink (above the price chart)."""
    img = img.copy()
    d = ImageDraw.Draw(img)
    f = font(52, bold=True)
    left, top, right, bottom = 200, 780, 1072 - 372, 1448 - 568
    w = d.textlength(text, font=f)
    x0 = (left + right - w) / 2
    d.rectangle([x0 - 16, top, x0 + w + 16, bottom], fill=0)
    d.text(((left + right) / 2, (top + bottom) / 2), text, font=f, fill=255, anchor="mm")
    return img


def on_paper(screen: Image.Image) -> Image.Image:
    """Grayscale screen -> RGB with the white mapped to paper tone."""
    rgb = screen.convert("RGB")
    lut = []
    for c in range(3):
        lut += [round(v * PAPER[c] / 255) for v in range(256)]
    return rgb.point(lut)


def device(screen: Image.Image, width: int) -> Image.Image:
    """Plain e-reader mockup: dark bezel, rounded corners, shadow."""
    scale = width / 1300
    sw, sh = round(1072 * scale), round(1448 * scale)
    side, top, chin = round(114 * scale), round(130 * scale), round(170 * scale)
    w, h = sw + 2 * side, sh + top + chin
    pad = round(40 * scale)
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [pad + 6, pad + 14, pad + w + 6, pad + h + 14], radius=round(70 * scale), fill=(0, 0, 0, 90)
    )
    from PIL import ImageFilter

    out = Image.alpha_composite(out, shadow.filter(ImageFilter.GaussianBlur(round(18 * scale))))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([pad, pad, pad + w, pad + h], radius=round(70 * scale), fill=BEZEL + (255,))
    out.paste(on_paper(screen).resize((sw, sh), Image.LANCZOS), (pad + side, pad + top))
    return out


def social(dev: Image.Image) -> Image.Image:
    img = Image.new("RGB", (1280, 640), (245, 244, 239))
    dev = dev.copy()
    dev.thumbnail((560, 620), Image.LANCZOS)
    img.paste(dev, (40, (640 - dev.height) // 2), dev)
    d = ImageDraw.Draw(img)
    x = 40 + dev.width + 40
    d.text((x, 150), "kindle-dashboard-fi", font=font(56, bold=True), fill=(20, 20, 20))
    lines = [
        ("Sää ja pörssisähkö vanhaan Kindleen", 34, True),
        ("Weather and spot electricity prices", 34, False),
        ("on an old jailbroken Kindle", 34, False),
    ]
    y = 240
    for text, size, bold in lines:
        d.text((x, y), text, font=font(size, bold), fill=(40, 40, 40))
        y += size + 16
    d.text((x, y + 30), "Mac mini · Python · FMI · porssisahko.net", font=font(26), fill=(100, 100, 100))
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    screen = render(demo())
    screen.save(OUT / "dashboard.png", optimize=True)
    error_banner(screen, "yhteysvirhe 03.15").save(OUT / "dashboard-error.png", optimize=True)
    low = render(demo(battery=15, low_battery=True))
    low.save(OUT / "dashboard-low-battery.png", optimize=True)
    dev = device(screen, 900)
    dev.save(OUT / "kindle.png", optimize=True)
    social(dev).save(OUT / "social-preview.png", optimize=True)
    for p in sorted(OUT.glob("*.png")):
        print(p.relative_to(ROOT), Image.open(p).size)


if __name__ == "__main__":
    main()
