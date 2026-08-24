"""Remove the profile-photo background and build a GitHub-safe reveal SVG."""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

from PIL import Image
from rembg import remove

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "profile.jpeg"
TRANSPARENT = ROOT / "generated" / "profile-transparent.png"
REVEAL = ROOT / "generated" / "profile-reveal.svg"
TAGS = (
    "SOFTWARE ENGINEER",
    "FULL-STACK DEVELOPER",
    "PRODUCT BUILDER",
    "SECURITY ENTHUSIAST",
    "FOUNDER",
)


def remove_photo_background(source: Path, output: Path) -> Image.Image:
    """Remove only the background; retain the source dimensions and foreground pixels."""
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
    tag_space = max(120, round(height * 0.10))
    tag_y = height + round(tag_space * 0.56)
    total_height = height + tag_space
    reveal_seconds = 3.4
    first_tag = 4.2
    tag_duration = 15
    encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'viewBox="0 0 {width} {total_height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Rohan Kumar</title>',
        '<desc id="desc">Profile photograph with a gently rotating professional role label.</desc>',
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
    for index, tag in enumerate(TAGS):
        begin = first_tag + index * 3
        lines.extend([
            f'<text x="{width / 2:.1f}" y="{tag_y}" text-anchor="middle" opacity="0" '
            'fill="#303030" font-family="JetBrains Mono,DejaVu Sans Mono,Consolas,monospace" '
            f'font-size="{max(20, round(width * 0.025))}" letter-spacing="2.2">{tag}',
            '<animate attributeName="opacity" values="0;1;1;0;0" '
            f'keyTimes="0;0.08;0.16;0.20;1" begin="{begin:.1f}s" dur="{tag_duration}s" '
            'repeatCount="indefinite"/>',
            '</text>',
        ])
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=SOURCE)
    parser.add_argument("--png", type=Path, default=TRANSPARENT)
    parser.add_argument("--svg", type=Path, default=REVEAL)
    args = parser.parse_args()
    photo = remove_photo_background(args.input, args.png)
    args.svg.write_text(reveal_svg(photo, args.png), encoding="utf-8")
    print(f"Wrote {args.png} and {args.svg} ({photo.width} x {photo.height})")


if __name__ == "__main__":
    main()
