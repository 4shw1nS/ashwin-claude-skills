#!/usr/bin/env python3
"""Merge two images side-by-side into a LinkedIn-tuned canvas.

- Auto-picks canvas: 1200x1200 (square) when both inputs are portrait/square,
  1200x627 (1.91:1 landscape) when both inputs are landscape, square otherwise.
- Each input gets exactly half the canvas width (symmetric panels).
- Images are resized to FIT the panel without cropping (letterbox/pillarbox).
- Empty padding is filled with a blurred, panel-cover version of the same
  image so each side feels intentional rather than empty.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


SQUARE = (1200, 1200)
LANDSCAPE = (1200, 628)  # LinkedIn 1.91:1; 628 keeps both panels even-width-friendly
PORTRAIT_THRESHOLD = 0.98   # h/w > 1/0.98 -> portrait; w/h > 1/0.98 -> landscape


def orientation(img: Image.Image) -> str:
    w, h = img.size
    ratio = w / h
    if ratio > 1 / PORTRAIT_THRESHOLD:
        return "landscape"
    if ratio < PORTRAIT_THRESHOLD:
        return "portrait"
    return "square"


def pick_canvas(img_a: Image.Image, img_b: Image.Image) -> tuple[int, int]:
    oa, ob = orientation(img_a), orientation(img_b)
    if oa == "landscape" and ob == "landscape":
        return LANDSCAPE
    return SQUARE


def fit_into_panel(img: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    """Resize preserving aspect so the entire image fits inside (panel_w, panel_h)."""
    src_w, src_h = img.size
    scale = min(panel_w / src_w, panel_h / src_h)
    new_w = max(1, round(src_w * scale))
    new_h = max(1, round(src_h * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)


def cover_panel(img: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    """Resize-and-crop so the image fully covers (panel_w, panel_h). Used for blurred fill."""
    src_w, src_h = img.size
    scale = max(panel_w / src_w, panel_h / src_h)
    new_w = max(panel_w, round(src_w * scale))
    new_h = max(panel_h, round(src_h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - panel_w) // 2
    top = (new_h - panel_h) // 2
    return resized.crop((left, top, left + panel_w, top + panel_h))


def make_panel(img: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    """Build one panel: blurred cover background + centered fitted foreground."""
    background = cover_panel(img, panel_w, panel_h)
    blur_radius = max(panel_w, panel_h) // 24  # ~50px for a 1200-wide canvas
    background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    # Slight darken so the foreground image stands out.
    background = Image.eval(background, lambda v: int(v * 0.78))

    foreground = fit_into_panel(img, panel_w, panel_h)
    fg_w, fg_h = foreground.size
    offset = ((panel_w - fg_w) // 2, (panel_h - fg_h) // 2)

    panel = background.copy()
    if foreground.mode == "RGBA":
        panel.paste(foreground, offset, foreground)
    else:
        panel.paste(foreground, offset)
    return panel


def load_image(path: Path) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # honor camera orientation
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    return img


def merge(img_a_path: Path, img_b_path: Path, out_path: Path,
          canvas_override: str | None = None) -> tuple[int, int]:
    img_a = load_image(img_a_path)
    img_b = load_image(img_b_path)

    if canvas_override == "square":
        canvas_w, canvas_h = SQUARE
    elif canvas_override == "landscape":
        canvas_w, canvas_h = LANDSCAPE
    else:
        canvas_w, canvas_h = pick_canvas(img_a, img_b)

    # Symmetric halves; if width is odd, the right panel absorbs the extra pixel.
    panel_w = canvas_w // 2
    right_w = canvas_w - panel_w
    panel_h = canvas_h

    left_panel = make_panel(img_a, panel_w, panel_h)
    right_panel = make_panel(img_b, right_w, panel_h)

    canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
    canvas.paste(left_panel, (0, 0))
    canvas.paste(right_panel, (panel_w, 0))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = out_path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        canvas.save(out_path, "JPEG", quality=92, optimize=True, progressive=True)
    elif suffix == ".png":
        canvas.save(out_path, "PNG", optimize=True)
    else:
        canvas.save(out_path)
    return canvas_w, canvas_h


def main() -> int:
    p = argparse.ArgumentParser(description="Merge two images side-by-side for LinkedIn.")
    p.add_argument("image_a", type=Path, help="Left image path")
    p.add_argument("image_b", type=Path, help="Right image path")
    p.add_argument("-o", "--output", type=Path, default=Path("merged_linkedin.jpg"),
                   help="Output path (default: ./merged_linkedin.jpg)")
    p.add_argument("--canvas", choices=["auto", "square", "landscape"], default="auto",
                   help="Canvas selection (default: auto)")
    args = p.parse_args()

    for path in (args.image_a, args.image_b):
        if not path.exists():
            print(f"error: input not found: {path}", file=sys.stderr)
            return 2

    canvas_override = None if args.canvas == "auto" else args.canvas
    w, h = merge(args.image_a, args.image_b, args.output, canvas_override)
    print(f"wrote {args.output} ({w}x{h})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
