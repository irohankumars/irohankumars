"""Remove the profile-photo background and build a GitHub-safe reveal SVG."""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "profile.jpeg"
TRANSPARENT = ROOT / "generated" / "profile-transparent.png"
REVEAL = ROOT / "generated" / "profile-reveal.svg"
def remove_photo_background(source: Path, output: Path) -> Image.Image:
    """Remove only the background; retain the source dimensions and foreground pixels."""
    from rembg import remove

    original = Image.open(source).convert("RGBA")
    result = remove(
        original,
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    ).convert("RGBA")
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "PNG", optimize=True)
    return result


def reveal_svg(photo: Image.Image, png_path: Path) -> str:
    width, height = photo.size
    reveal_seconds = 3.4
    encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Rohan Kumar</title>',
        '<desc id="desc">Profile photograph with a gentle top-to-bottom reveal.</desc>',
        '<defs>',
        '<clipPath id="photo-reveal">',
        f'<rect x="0" y="0" width="{width}" height="0">',
        f'<animate attributeName="height" from="0" to="{height}" dur="{reveal_seconds}s" '
        'calcMode="spline" keySplines="0.45 0 0.15 1" fill="freeze"/>',
        '</rect>',
        '</clipPath>',
        '</defs>',
        f'<image x="0" y="0" width="{width}" height="{height}" '
        f'preserveAspectRatio="xMidYMid meet" clip-path="url(#photo-reveal)" '
        f'href="data:image/png;base64,{encoded}"/>',
    ]
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=SOURCE)
    parser.add_argument("--png", type=Path, default=TRANSPARENT)
    parser.add_argument("--svg", type=Path, default=REVEAL)
    parser.add_argument("--reuse-png", action="store_true", help="Rebuild the reveal SVG without rerunning background removal")
    args = parser.parse_args()
    photo = Image.open(args.png).convert("RGBA") if args.reuse_png else remove_photo_background(args.input, args.png)
    args.svg.write_bytes(reveal_svg(photo, args.png).encode("utf-8"))
    print(f"Wrote {args.png} and {args.svg} ({photo.width} x {photo.height})")


if __name__ == "__main__":
    main()
