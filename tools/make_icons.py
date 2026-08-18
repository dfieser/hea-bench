#!/usr/bin/env python3
"""Generate the desktop and web icon sets from the HEA-Bench mark.

The mark: the app's hexagon (the titlebar's U+2B22 glyph) in the brand
terracotta, carrying a cream hexagonal close-packed lattice — seven
nodes, center bonded to ring, ring bonded around — the crystallography
the calculator is about. Flat two-tone so it survives 16 px.

Two tunings of the same geometry, because the two surfaces are viewed at
different sizes. DESKTOP is the original: hairline bonds that stay
elegant on a 256 px launcher tile. WEB thickens the bonds and nodes and
widens the rim, because a browser tab and a Google result render the mark
at 16-32 px, where the desktop tuning's bonds fall under one pixel and
turn to mush.

Writes, for the desktop, every file referenced by
src-tauri/tauri.conf.json plus the Windows tile set, the multi-size
icon.ico, and a PNG-chunk icon.icns. Writes, for the web, the crawlable
favicon set, the PWA icons, and the 1200x630 social card. Deterministic:
same script, same bytes (PNG metadata aside).

Run from the repo root::

    python tools/make_icons.py

tools/preflight.py checks the web outputs still exist and are the right
shape, so a push cannot quietly drop them.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "src-tauri" / "icons"
WEB = ROOT / "web"

TERRACOTTA = (139, 58, 47, 255)   # --accent  #8b3a2f
RIM = (94, 42, 35, 255)           # --accent-2 #5e2a23
CREAM = (250, 248, 243, 255)      # --bg      #faf8f3
INK = (27, 27, 24, 255)           # --text    #1b1b18
MUTED = (90, 90, 82, 255)         # --text-muted #5a5a52

SS = 4096  # supersampled master canvas
U = SS / 100  # one unit of the 100-unit design space the web mark is specified in

#: Geometry of the mark, in supersampled canvas units. Radii are
#: circumradii of the hexagons; the rim shows as the difference between
#: ``rim_r`` and ``face_r``.
DESKTOP = dict(rim_r=1980, face_r=1860, ring_r=980, bond=74, node_r=168, center_r=210)

#: The web tuning, specified in the 100-unit space of web/favicon.svg so
#: the vector and the rasters stay one drawing.
WEB_MARK = dict(
    rim_r=48 * U, face_r=43 * U, ring_r=24 * U,
    bond=3.5 * U, node_r=5 * U, center_r=6 * U,
)

#: The 16 px tuning. Optical sizing, not a second logo: it is WEB_MARK
#: with the ring bonds and ring nodes dropped and the spokes fattened.
#: The full lattice at 16 px puts three cream features inside five
#: pixels and averages to a pink smudge; the bare spokes still read as
#: an atom bonded to its neighbours.
SMALL_MARK = dict(
    rim_r=48 * U, face_r=43 * U, ring_r=24 * U,
    bond=5.5 * U, node_r=0, center_r=9 * U, ring_bonds=False,
)


def hexagon(cx: float, cy: float, r: float, rotation_deg: float) -> list[tuple[float, float]]:
    return [
        (cx + r * math.cos(math.radians(rotation_deg + 60 * k)),
         cy + r * math.sin(math.radians(rotation_deg + 60 * k)))
        for k in range(6)
    ]


def draw_master(
    rim_r: float, face_r: float, ring_r: float,
    bond: float, node_r: float, center_r: float,
    ring_bonds: bool = True,
) -> Image.Image:
    img = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = SS / 2

    # Pointy-top hexagon silhouette with a darker rim for definition on
    # light desktops.
    d.polygon(hexagon(c, c, rim_r, -90), fill=RIM)
    d.polygon(hexagon(c, c, face_r, -90), fill=TERRACOTTA)

    # Cream lattice: center node bonded to a flat-top ring of six.
    ring = hexagon(c, c, ring_r, -60)
    for x, y in ring:
        d.line([(c, c), (x, y)], fill=CREAM, width=round(bond))
    if ring_bonds:
        for i in range(6):
            d.line([ring[i], ring[(i + 1) % 6]], fill=CREAM, width=round(bond))
    if node_r:
        for x, y in ring:
            d.ellipse([x - node_r, y - node_r, x + node_r, y + node_r], fill=CREAM)
    d.ellipse([c - center_r, c - center_r, c + center_r, c + center_r], fill=CREAM)
    return img


def sized(master: Image.Image, px: int) -> Image.Image:
    return master.resize((px, px), Image.LANCZOS)


def write_icns(master: Image.Image, path: Path) -> None:
    """Minimal ICNS writer using PNG-encoded chunks (macOS 10.7+)."""
    types = [
        (b"icp4", 16), (b"icp5", 32), (b"ic11", 32), (b"ic12", 64),
        (b"ic07", 128), (b"ic13", 256), (b"ic08", 256), (b"ic14", 512),
        (b"ic09", 512), (b"ic10", 1024),
    ]
    chunks = b""
    for tag, px in types:
        import io

        buf = io.BytesIO()
        sized(master, px).save(buf, format="PNG")
        data = buf.getvalue()
        chunks += tag + struct.pack(">I", len(data) + 8) + data
    path.write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)


def _hex_svg(r: float, rotation_deg: float) -> str:
    pts = hexagon(50, 50, r, rotation_deg)
    return " ".join(f"{x:.4g},{y:.4g}" for x, y in pts)


def write_favicon_svg(path: Path) -> None:
    """Emit the vector favicon from the same numbers the rasters use.

    Modern browsers prefer this one; it is the only icon that stays sharp
    on a 3x display. The rasters below exist for everything that cannot
    read SVG, Google's result favicon included.
    """
    m = {k: v / U for k, v in WEB_MARK.items()}  # back to the 100-unit space
    ring = hexagon(50, 50, m["ring_r"], -60)
    bonds = "".join(f"M50 50L{x:.4g} {y:.4g}" for x, y in ring)
    bonds += "".join(
        f"M{ring[i][0]:.4g} {ring[i][1]:.4g}L{ring[(i + 1) % 6][0]:.4g} {ring[(i + 1) % 6][1]:.4g}"
        for i in range(6)
    )
    nodes = "".join(
        f'<circle cx="{x:.4g}" cy="{y:.4g}" r="{m["node_r"]:.4g}"/>' for x, y in ring
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        "<title>HEA-Bench</title>"
        f'<polygon points="{_hex_svg(m["rim_r"], -90)}" fill="#5e2a23"/>'
        f'<polygon points="{_hex_svg(m["face_r"], -90)}" fill="#8b3a2f"/>'
        f'<path d="{bonds}" stroke="#faf8f3" stroke-width="{m["bond"]:.4g}" fill="none"/>'
        f'<g fill="#faf8f3"><circle cx="50" cy="50" r="{m["center_r"]:.4g}"/>{nodes}</g>'
        "</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def _font(name: str, px: int) -> ImageFont.FreeTypeFont:
    """Load a DejaVu face, which ships with matplotlib on every platform.

    Keeping the font inside a Python package rather than the OS is what
    makes the social card reproducible on Windows, macOS and CI alike.
    """
    try:
        import matplotlib
    except ImportError as exc:  # pragma: no cover - environment problem
        raise SystemExit(
            "the social card needs the DejaVu fonts bundled with matplotlib; "
            "run: python -m pip install matplotlib"
        ) from exc
    path = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf" / name
    if not path.exists():  # pragma: no cover - environment problem
        raise SystemExit(f"font {name} not found at {path}; run: python -m pip install -U matplotlib")
    return ImageFont.truetype(str(path), px)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def write_og_card(master: Image.Image, path: Path) -> None:
    """The 1200x630 card shown when the site is linked anywhere social.

    Set in the site's own register: cream stock, serif wordmark, hairline
    rules, the citation in the footer. It has to read as a research tool
    at thumbnail size, so the mark and the wordmark carry it and
    everything else is secondary.
    """
    w, h = 1200, 630
    card = Image.new("RGB", (w, h), CREAM[:3])
    d = ImageDraw.Draw(card)

    # Brand bar along the top edge: the one element that still reads when
    # a client crops the card to a strip.
    d.rectangle([0, 0, w, 12], fill=TERRACOTTA[:3])

    mark_px = 250
    mark_x, mark_y = 84, (h - mark_px) // 2 + 6
    card.paste(sized(master, mark_px), (mark_x, mark_y), sized(master, mark_px))

    x = mark_x + mark_px + 66
    right = w - 84

    wordmark = _font("DejaVuSerif-Bold.ttf", 88)
    d.text((x, 196), "HEA-Bench", font=wordmark, fill=INK[:3], anchor="ls")

    d.line([(x, 232), (right, 232)], fill=(217, 214, 204), width=2)

    tagline = _font("DejaVuSerif.ttf", 31)
    lines = _wrap(
        d,
        "The standard descriptors for high-entropy alloys and oxides, with the work shown.",
        tagline,
        right - x,
    )
    y = 286
    for line in lines:
        d.text((x, y), line, font=tagline, fill=MUTED[:3], anchor="ls")
        y += 46

    mono = _font("DejaVuSansMono.ttf", 25)
    d.text((x, 452), "dfieser.github.io/hea-bench", font=mono, fill=TERRACOTTA[:3], anchor="ls")

    cite = _font("DejaVuSerif.ttf", 23)
    d.text(
        (x, 494),
        "Materials 2026, 19(14), 3075 · doi:10.3390/ma19143075",
        font=cite,
        fill=(138, 136, 128),
        anchor="ls",
    )

    card.save(path, optimize=True)


def write_web_icons(master: Image.Image, small: Image.Image) -> list[str]:
    """The crawlable icon set for the GitHub Pages site.

    Every path here is referenced with a RELATIVE href from
    web/index.html. hea-bench is a GitHub *project* page served from
    /hea-bench/, so a root-absolute /favicon.ico would resolve against
    dfieser.github.io, which this repository does not own.
    """
    written: list[str] = []

    write_favicon_svg(WEB / "favicon.svg")
    written.append("favicon.svg")

    # 48 px is the size Google's result-favicon crawler asks for; 16 and
    # 32 are what browsers actually paint in the tab. The 16 px frame
    # carries SMALL_MARK, the rest carry the full lattice. Pillow drops
    # any requested size larger than the base image, so the base has to
    # be the largest frame and the smaller ones ride in append_images.
    sized(master, 48).save(
        WEB / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[sized(small, 16), sized(master, 32)],
    )
    written.append("favicon.ico")

    for name, px in {
        "apple-touch-icon.png": 180,  # iOS home screen, no transparency allowed
        "icon-192.png": 192,
        "icon-512.png": 512,
    }.items():
        img = sized(master, px)
        if name.startswith("apple"):
            flat = Image.new("RGB", (px, px), CREAM[:3])
            flat.paste(img, (0, 0), img)
            img = flat
        img.save(WEB / name, optimize=True)
        written.append(name)

    write_og_card(master, WEB / "og-image.png")
    written.append("og-image.png")
    return written


def main() -> None:
    master = draw_master(**DESKTOP)

    pngs = {
        "icon.png": 512,
        "128x128.png": 128,
        "128x128@2x.png": 256,
        "32x32.png": 32,
        "StoreLogo.png": 50,
        "Square30x30Logo.png": 30,
        "Square44x44Logo.png": 44,
        "Square71x71Logo.png": 71,
        "Square89x89Logo.png": 89,
        "Square107x107Logo.png": 107,
        "Square142x142Logo.png": 142,
        "Square150x150Logo.png": 150,
        "Square284x284Logo.png": 284,
        "Square310x310Logo.png": 310,
    }
    for name, px in pngs.items():
        sized(master, px).save(ICONS / name)

    sized(master, 256).save(
        ICONS / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    write_icns(master, ICONS / "icon.icns")
    print(f"wrote {len(pngs)} PNGs + icon.ico + icon.icns to {ICONS}")

    web_files = write_web_icons(draw_master(**WEB_MARK), draw_master(**SMALL_MARK))
    print(f"wrote {', '.join(web_files)} to {WEB}")


if __name__ == "__main__":
    main()
