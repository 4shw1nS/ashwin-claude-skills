# examples/

Sample inputs you can feed straight into `scripts/build_board.py` to see the
skill in action.

## smoke-test.json

A small, deliberate exercise of the board's features. Run:

```bash
python3 ../scripts/build_board.py --data smoke-test.json \
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

## See also

- `../scripts/make_demo.py` — regenerates the captioned MP4/GIF demo from this
  smoke board (action-first storyboard: drag a card live, then walk through the
  feature set). See the script's docstring for details and the `HOLD`/`FADE`
  knobs at the top.
