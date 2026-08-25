"""Generate the large, GitHub-compatible animated identity tag."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "generated" / "profile-tag.svg"
PHRASE = "SOFTWARE ENGINEER"


def make_svg() -> str:
    width, height, font_size = 560, 82, 40
    char_width = font_size * 0.62
    text_width = len(PHRASE) * char_width
    text_x = (width - text_width) / 2
    widths = ";".join(f"{step * char_width:.1f}" for step in range(len(PHRASE) + 1))
    key_times = ";".join(f"{step / len(PHRASE):.5f}" for step in range(len(PHRASE) + 1))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="tag-title tag-desc">',
        '<title id="tag-title">Rohan Kumar | software engineer</title>',
        '<desc id="tag-desc">Software Engineer appears once with a subtle typewriter reveal.</desc>',
        '<defs>',
        f'<clipPath id="tag-reveal"><rect x="{text_x:.1f}" y="0" width="0" height="{height}">',
        f'<animate attributeName="width" values="{widths}" keyTimes="{key_times}" dur="1.8s" '
        'calcMode="discrete" fill="freeze"/>',
        '</rect></clipPath>',
        '</defs>',
        f'<text x="{width / 2:.1f}" y="55" text-anchor="middle" clip-path="url(#tag-reveal)" fill="#39d353" '
        f'font-family="JetBrains Mono,DejaVu Sans Mono,Consolas,monospace" font-size="{font_size}" '
        f'font-weight="600" letter-spacing="1.2">{PHRASE}</text>',
    ]
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(make_svg().encode("utf-8"))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
