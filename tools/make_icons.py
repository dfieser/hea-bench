#!/usr/bin/env python3
"""Generate the desktop app icon set from the HEA-Bench mark.

The mark: the app's hexagon (the titlebar's U+2B22 glyph) in the brand
terracotta, carrying a cream hexagonal close-packed lattice — seven
nodes, center bonded to ring, ring bonded around — the crystallography
the calculator is about. Flat two-tone so it survives 16 px.

Writes every file referenced by src-tauri/tauri.conf.json plus the
Windows tile set, the multi-size icon.ico, and a PNG-chunk icon.icns.
Deterministic: same script, same bytes (PNG metadata aside).

Run from the repo root::

    python tools/make_icons.py
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "src-tauri" / "icons"

TERRACOTTA = (139, 58, 47, 255)   # --accent  #8b3a2f
RIM = (94, 42, 35, 255)           # --accent-2 #5e2a23
CREAM = (250, 248, 243, 255)      # --bg      #faf8f3

SS = 4096  # supersampled master canvas


def hexagon(cx: float, cy: float, r: float, rotation_deg: float) -> list[tuple[float, float]]:
    return [
        (cx + r * math.cos(math.radians(rotation_deg + 60 * k)),
         cy + r * math.sin(math.radians(rotation_deg + 60 * k)))
        for k in range(6)
    ]


def draw_master() -> Image.Image:
    img = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = SS / 2

    # Pointy-top hexagon silhouette with a darker rim for definition on
    # light desktops.
    d.polygon(hexagon(c, c, 1980, -90), fill=RIM)
    d.polygon(hexagon(c, c, 1860, -90), fill=TERRACOTTA)

    # Cream lattice: center node bonded to a flat-top ring of six.
    ring = hexagon(c, c, 980, -60)
    bond = 74
    for x, y in ring:
        d.line([(c, c), (x, y)], fill=CREAM, width=bond)
    for i in range(6):
        d.line([ring[i], ring[(i + 1) % 6]], fill=CREAM, width=bond)
    for x, y in ring:
        rr = 168
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=CREAM)
    rr = 210
    d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=CREAM)
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


def main() -> None:
    master = draw_master()

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


if __name__ == "__main__":
    main()
