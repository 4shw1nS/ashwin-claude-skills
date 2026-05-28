# linkedin-image-merge

Merge two images side-by-side into a **LinkedIn-ready post**. Both panels get
exactly half the canvas, neither image is cropped, and any leftover space is
filled with a blurred extension of that same image — so the result never looks
like raw letterbox bars.

```
[ portrait A ]  +  [ landscape B ]   →   1200×1200 (or 1200×628), no crop,
                                          blurred padding inside each panel
```

---

## Try it in 30 seconds

```bash
git clone https://github.com/4shw1nS/ashwin-claude-skills.git
cp -R ashwin-claude-skills/linkedin-image-merge ~/.claude/skills/

python3 ~/.claude/skills/linkedin-image-merge/scripts/merge_images.py \
  left.jpg right.jpg -o merged.jpg
```

In Claude Code: type `/linkedin-image-merge` and point at two image files;
Claude resolves paths, picks the canvas, and surfaces the output dimensions.

Depends only on Pillow (already installed on most Macs via Homebrew).

---

## What it guarantees

| | |
|---|---|
| ⚖️ **Equal halves** | Both panels are exactly `canvas_width / 2` wide. Symmetry holds even when the two inputs have wildly different aspect ratios. |
| 🚫 **No subject crop** | Each image is LANCZOS-resized to *fit* inside its panel — letterboxed / pillarboxed if needed. The full image is always visible. |
| 🌫 **Blurred padding** | The leftover space inside a panel is filled with a blurred, slightly darkened, panel-cover version of that same image. No black bars. |
| 📐 **LinkedIn-tuned canvas** | Auto-picks `1200×628` (1.91:1 landscape) when both inputs are landscape, otherwise `1200×1200` (square). Both are formats LinkedIn renders without re-cropping. |

---

## Flags

| Flag | Default | Description |
|---|---|---|
| `-o`, `--output PATH` | `./merged_linkedin.jpg` | Output path. Extension (`.jpg`, `.jpeg`, `.png`) controls format. JPEG is saved at quality 92, progressive. |
| `--canvas auto\|square\|landscape` | `auto` | Override the auto canvas pick. |

---

## Edge cases the script already handles

- **EXIF rotation** — `ImageOps.exif_transpose` is applied, so phone photos
  taken in portrait don't merge sideways.
- **RGBA / palette inputs** — converted to RGB (or composited with alpha) so
  JPEG output never errors.
- **Odd canvas widths** — left panel takes the floor, right panel absorbs the
  extra pixel. Visually imperceptible at 1200 px.
- **Mismatched aspects** — covered by the fit-then-blurred-fill approach.

---

## File map

```
linkedin-image-merge/
├── SKILL.md              ← Claude reads this
├── README.md             ← (this file)
└── scripts/
    └── merge_images.py   ← Pillow-only, ~150 LOC, no external deps beyond Pillow
```

---

## When NOT to use this

- You want a **vertical (stacked)** merge — this is side-by-side only.
- You want **three or more** images — out of scope; use a grid tool.
- You want **captions / logos / watermarks** burned in — out of scope.

---

## License

[MIT](../LICENSE) © Ashwin Sinha
