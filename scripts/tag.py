"""Generate the large, GitHub-compatible animated identity tag."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "generated" / "profile-tag.svg"
PHRASES = (
    "SOFTWARE ENGINEER",
    "FULL-STACK DEVELOPER",
    "PRODUCT BUILDER",
    "SECURITY ENTHUSIAST",
)


def animation(phrase: str, index: int, duration: float) -> tuple[str, str]:
    phase = duration / len(PHRASES)
    start = index * phase
    type_end = start + 1.35
    hold_end = start + 2.25
    delete_end = start + 2.85
    widths = [0]
    times = [0.0]
    if start > 0:
        widths.append(0)
        times.append(start)
    for step in range(1, len(phrase) + 1):
        widths.append(step)
        times.append(start + (type_end - start) * step / len(phrase))
    widths.append(len(phrase))
    times.append(hold_end)
    for step in range(len(phrase) - 1, -1, -1):
        widths.append(step)
        times.append(hold_end + (delete_end - hold_end) * (len(phrase) - step) / len(phrase))
    widths.append(0)
    times.append(duration)
    values = ";".join(str(value) for value in widths)
    key_times = ";".join(f"{value / duration:.5f}" for value in times)
    return values, key_times


def make_svg() -> str:
    width, height, font_size = 760, 92, 42
    duration = 12.0
    char_width = font_size * 0.62
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 92" role="img" aria-labelledby="tag-title tag-desc">',
        '<title id="tag-title">Rohan Kumar — software engineer and product builder</title>',
        '<desc id="tag-desc">A large green typewriter animation cycles through professional roles.</desc>',
        '<defs>',
    ]
    for index, phrase in enumerate(PHRASES):
        text_width = len(phrase) * char_width
        x = (width - text_width) / 2
        values, key_times = animation(phrase, index, duration)
        pixel_values = ";".join(f"{int(value) * char_width:.1f}" for value in map(int, values.split(";")))
        parts.extend([
            f'<clipPath id="tag-{index}"><rect x="{x:.1f}" y="0" width="0" height="{height}">',
            f'<animate attributeName="width" values="{pixel_values}" keyTimes="{key_times}" '
            f'dur="{duration}s" calcMode="discrete" repeatCount="indefinite"/>',
            '</rect></clipPath>',
        ])
    parts.append('</defs>')
    for index, phrase in enumerate(PHRASES):
        text_width = len(phrase) * char_width
        x = (width - text_width) / 2
        parts.append(
            f'<text x="{x:.1f}" y="60" clip-path="url(#tag-{index})" fill="#39d353" '
            f'font-family="JetBrains Mono,DejaVu Sans Mono,Consolas,monospace" font-size="{font_size}" '
            f'font-weight="600" letter-spacing="1.2">{phrase}</text>'
        )
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(make_svg().encode("utf-8"))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
