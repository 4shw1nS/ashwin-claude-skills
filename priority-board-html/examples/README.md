# examples/

Sample inputs you can feed straight into `build_board.py` to see the skill in action.

## smoke-test.json

A small, deliberate exercise of the board's features. Run:

```bash
python3 ../build_board.py --data smoke-test.json \
  --title "Smoke Test Board" --out /tmp/smoke.html
open /tmp/smoke.html
```

What each card demonstrates:

| card | what it exercises |
|------|-------------------|
| **Now** has `wipLimit: 2` with **3 cards** | over-limit pill (red `3/2`); click the pill to change the cap |
| **T-4** estimate `5.5` | `build_board.py` float preservation (renders as `5.5 pts`) |
| **T-5** due **today** | timezone-safe `isOverdue` (must NOT render as overdue) |
| **T-7** `enteredLaneAt: 2026-05-05` | aging chip — should show amber "🕒 23d in lane" |
| every card has a `rationale` | toggle the **💡** button to hide them all |
| labels + priorities + assignees | open the **Filters** chip row to filter on any of them |
| 8 cards across all 4 lanes | drag, multi-select (⇧+click / ⌘+click), `j`/`k` nav, `1`–`4` to fling, `⌘Z` to undo |

## make-demo-gif.py

Regenerates a captioned demo of the board's features. Produces **both** an MP4
(primary, ~500 KB) and a GIF (fallback, ~2.5 MB) — the MP4 looks much smoother
because h.264 handles the crossfade transitions in a tenth the bytes.
Requires `ffmpeg` and Google Chrome on macOS.

What it does:

1. Builds the smoke board into `/tmp/pb_smoke.html`.
2. For each of 8 demo states (default → expanded → filters → text search →
   bulk select → hide rationale → inline edit → WIP at-limit), copies the HTML,
   forces `data-theme="dark"`, clears localStorage, and injects a `<script>`
   that puts the page into that state plus a fixed-position caption strip.
3. Headless-Chromes a 1500×900 screenshot of each variant.
4. Chains them with `xfade` crossfades (1.8 s hold + 0.35 s fade per frame),
   adds a final crossfade back to frame 1 so the loop restart is seamless,
   and emits an h.264 MP4. Then quantizes that MP4 to GIF using a bayer:5
   palette + `diff_mode=rectangle` so static "hold" regions dedup cleanly.

```bash
python3 make-demo-gif.py
# → priority-board-demo.mp4  +  priority-board-demo.gif
# in your Desktop's Claude working dir
```

Edit `FRAMES`, `OUT_DIR`, `HOLD`/`FADE` at the top to retarget.
