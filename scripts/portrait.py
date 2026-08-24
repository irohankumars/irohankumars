"""Turn assets/profile.jpeg into an animated ASCII SVG portrait."""
from __future__ import annotations
import argparse, html
from pathlib import Path
RAMP = " .`:-=+*cs#%@"
ROOT = Path(__file__).resolve().parents[1]

def remove_background(path: Path):
    import numpy as np
    from PIL import Image
    image = Image.open(path).convert("RGBA")
    try:
        from rembg import remove
        subject = remove(image)
    except Exception as error:
        print(f"Background removal unavailable ({error}); using source image.")
        subject = image
    canvas = Image.new("RGBA", subject.size, "white")
    canvas.alpha_composite(subject)
    return np.asarray(canvas.convert("RGB"))

def crop_subject(image):
    import cv2
    import numpy as np
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    points = cv2.findNonZero((gray < 248).astype(np.uint8))
    if points is None:
        return image
    x, y, width, height = cv2.boundingRect(points)
    px, py = int(width * .10), int(height * .06)
    return image[max(0,y-py):min(image.shape[0],y+height+py), max(0,x-px):min(image.shape[1],x+width+px)]

def to_ascii(image, columns: int) -> list[str]:
    import cv2
    import numpy as np
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    gray = cv2.createCLAHE(2.5, (8, 8)).apply(gray)
    gray = (np.power(gray.astype(np.float32) / 255, 1.7) * 255).astype(np.uint8)
    rows = max(1, round(columns * gray.shape[0] / gray.shape[1] * .48))
    pixels = cv2.resize(gray, (columns, rows), interpolation=cv2.INTER_AREA)
    # Dark pixels use dense glyphs; white pixels stay as whitespace.
    indexes = ((255 - pixels.astype(float)) / 255 * (len(RAMP) - 1)).astype(int)
    return ["".join(RAMP[i] for i in row) for row in indexes]

def make_svg(rows: list[str], columns: int, display_width: int) -> str:
    cw, lh, fs = 7.72, 15.2, 12.8
    width, height = columns * cw, (len(rows) + 1) * lh
    duration = min(3.2, max(1.8, len(rows) * .045))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{display_width}" viewBox="0 0 {width:.1f} {height:.1f}" role="img" aria-labelledby="title desc">',
        '<title id="title">ASCII portrait of Rohan Kumar</title>',
        '<desc id="desc">A monochrome portrait rendered with ASCII characters.</desc>',
        '<rect width="100%" height="100%" fill="#fff"/>',
        f'<defs><clipPath id="reveal"><rect width="100%" height="0"><animate attributeName="height" from="0" to="{height:.1f}" dur="{duration:.2f}s" fill="freeze"/></rect></clipPath></defs>',
        f'<g clip-path="url(#reveal)" fill="#161616" font-family="JetBrains Mono,DejaVu Sans Mono,Consolas,monospace" font-size="{fs}">'
    ]
    parts += [f'<text x="0" y="{(i+1)*lh:.1f}" xml:space="preserve">{html.escape(row)}</text>' for i,row in enumerate(rows)]
    parts += ['</g>', f'<rect width="{width:.1f}" height="1.4" fill="#707070" opacity="0"><animate attributeName="y" from="0" to="{height:.1f}" dur="{duration:.2f}s" fill="freeze"/><animate attributeName="opacity" values="0;0.38;0" keyTimes="0;0.05;1" dur="{duration:.2f}s" fill="freeze"/></rect>', '</svg>']
    return "\n".join(parts) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "assets/profile.jpeg")
    parser.add_argument("--output", type=Path, default=ROOT / "generated/portrait.svg")
    parser.add_argument("--columns", type=int, default=90)
    parser.add_argument("--width", type=int, default=460)
    args = parser.parse_args()
    rows = to_ascii(crop_subject(remove_background(args.input)), args.columns)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(make_svg(rows, args.columns, args.width), encoding="utf-8")
    print(f"Wrote {args.output} ({args.columns} columns x {len(rows)} rows)")

if __name__ == "__main__":
    main()
