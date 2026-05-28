---
name: linkedin-image-merge
description: >
  Merge two images side-by-side into a LinkedIn-ready post. Each image gets
  exactly half the canvas, is resized (never cropped) to fit, and any leftover
  space is filled with a blurred extension of that same image. Use when the
  user asks to "merge two images for LinkedIn", "combine these photos side by
  side", "make a LinkedIn collage", or invokes /linkedin-image-merge.
---

# LinkedIn Image Merge

Produce a symmetric, LinkedIn-tuned side-by-side merge of two input images.

## Guarantees this skill enforces

1. **Equal halves.** Both panels are exactly `canvas_width / 2` wide. Symmetry is preserved even when the two inputs have different aspect ratios.
2. **No cropping of subject content.** Each image is resized (LANCZOS) to FIT inside its panel — letterboxed/pillarboxed if needed. The full image is always visible.
3. **Blurred padding.** Empty space inside a panel is filled with a blurred, slightly darkened, panel-cover version of that same image, so panels never look like raw bars.
4. **LinkedIn-tuned canvas.** Auto-picks `1200x628` (1.91:1 landscape) when both inputs are landscape, otherwise `1200x1200` (square) — both are formats LinkedIn renders without re-cropping.

## How to run it

The script lives next to this file at `~/.claude/skills/linkedin-image-merge/scripts/merge_images.py` and depends only on Pillow (already installed on this machine via Homebrew).

```bash
python3 ~/.claude/skills/linkedin-image-merge/scripts/merge_images.py \
    <left_image> <right_image> \
    -o <output_path>
```

Default output is `./merged_linkedin.jpg` in the current working directory.

### Optional flags

- `--canvas auto|square|landscape` — override the auto pick. Default is `auto`.
- `-o, --output PATH` — output path. Extension (`.jpg`, `.jpeg`, `.png`) controls format. JPEG is saved at quality 92, progressive.

## What you (the assistant) should do when invoked

1. Confirm both input image paths from the user. Resolve them to absolute paths.
2. Pick an output filename: default to `merged_linkedin.jpg` in the user's current working directory unless they specified one.
3. Run the script with `python3`. Surface its stdout (it prints the final dimensions).
4. After it succeeds, briefly tell the user the canvas size that was chosen and where the file was written. Don't re-explain the algorithm unless asked.

## Edge cases the script already handles

- **EXIF rotation** — `ImageOps.exif_transpose` is applied so phone photos taken in portrait don't merge sideways.
- **RGBA / palette inputs** — converted to RGB (or composited with alpha) so JPEG output never errors.
- **Odd canvas widths** — left panel takes the floor, right panel absorbs the extra pixel. Visually imperceptible at 1200px.
- **Mismatched aspects** — covered by the fit-then-blurred-fill approach. No special handling needed.

## When NOT to use this skill

- The user wants a vertical (stacked) merge — this skill is side-by-side only. Tell them and offer to extend the script.
- The user wants three or more images — out of scope; recommend a grid tool.
- The user wants captions, logos, or watermarks burned in — out of scope.
