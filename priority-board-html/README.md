# priority-board-html

Turn any list of work items into a **single self-contained HTML drag-and-drop
priority board** with **Now / Next / Later / Cut** swim lanes. Cards are
pre-sorted by Claude, then you (or your team) refine by dragging. No server,
no internet, no dependencies — one `.html` file the recipient double-clicks.

```
spreadsheet ─┐
Linear/Jira ─┤   parse → Claude classifies → build →   one-file HTML board
pasted list ─┤
JSON state ──┘
```

---

## Try it in 30 seconds

```bash
git clone https://github.com/4shw1nS/ashwin-claude-skills.git
cp -R ashwin-claude-skills/priority-board-html ~/.claude/skills/

python3 ~/.claude/skills/priority-board-html/scripts/build_board.py \
  --data  ~/.claude/skills/priority-board-html/examples/smoke-test.json \
  --title "Smoke Test Board" \
  --out   /tmp/board.html
open /tmp/board.html
```

In Claude Code: type `/priority-board-html` and hand over a file path, a
URL to a CSV, or a pasted list. Claude takes care of the parse + classify
steps and gives you the HTML.

---

## What you can do in the board

| | |
|---|---|
| 🎯 **Drag** | Cards move between Now / Next / Later / Cut by dragging the ⠿ handle. Works on mouse, trackpad, and touch. |
| 🚦 **WIP limits** | Per-lane soft cap. Count pill turns amber at the limit, red over it. Click any count pill to set a limit. Pre-seedable in the input JSON. |
| ↶ **Undo (⌘Z)** | 30-step history. Every drag, edit, delete, lane rename, WIP change is undoable. |
| 🔢 **Bulk select** | `⇧+click` for range, `⌘+click` for toggle. Dragging any selected card moves the whole group. |
| ⌨️ **Keyboard nav** | `j`/`k` move focus, `1`–`4` fling to lane, `e` edit, `Enter` expand, `Del` delete, `/` focus search, `Esc` clear. |
| 🔍 **Filter & search** | Toggleable chip row (priority / owner / label, auto-built from your data) plus text search across id / title / desc / labels / assignee. |
| ✏️ **Inline edit** | Pencil icon opens a form for every field — id, lane, priority, estimate, status, owner, due date, labels, rationale, description, URL. |
| 🕒 **Aging** | Cards track when they entered the current lane; a "🕒 Nd in lane" chip appears at 3 days, turns amber at 14, the card fades at 30. |
| 💡 **Rationale toggle** | One click hides every card's rationale to declutter; choice persists per browser. |
| 🌓 **Dark / light theme** | Auto-respects your preference; toggle in toolbar. |
| 📋 **Markdown export** | One-click copy of the board as a Markdown doc (lane headers + bulleted cards) — perfect for standup notes. |
| 🖨 **Print stylesheet** | `⌘P` produces a clean printable view: lanes stack, all descriptions expand, chrome hides. |
| 💾 **Auto-save + file save** | Real-time `localStorage` save per browser, plus **Save HTML** (durable, shareable) and **JSON** export / **Load** for cross-machine persistence. |

---

## Inputs accepted

`scripts/parse_input.py` normalizes any of these into the canonical shape:

- `.csv`, `.tsv`, `.xlsx`, `.json` files
- Linear / Jira / GitHub Issues exports
- Pasted markdown tables or bullet lists (Claude handles those itself)
- Google Sheets — download as CSV first

Column headers are matched fuzzily (e.g. `Issue Title`, `issue_title`,
`ISSUETITLE` all map to `title`). Unknown columns are preserved under each
card's `extra` field. See [`reference.md`](reference.md) for the full alias
table and lane-scoring rubric.

---

## Persistence story

**Working autosave** — every mutation writes to `localStorage` after a 250 ms
debounce, namespaced by `boardId` so multiple boards on the same `file://`
origin never collide. Watch the toolbar for *"Saved · 11:43:02"*.

**Cross-machine, cross-session** — three buttons in the toolbar:

- **⬇ Save HTML** — re-bakes current state into a fresh self-contained `.html`
  with a new `boardId`. Email it, drop it in a shared drive, fork it.
- **⬇ JSON** — exports the board state (`{version, boardId, title, lanes,
  cards, updatedAt}`) for git, Slack, or programmatic use.
- **⬆ Load** — restores a JSON export into the current board.

What it deliberately does **not** do: live two-way sync with Linear / Jira /
Sheets, or multi-user real-time collaboration. It's a single-file, single-
author snapshot tool.

---

## File map

```
priority-board-html/
├── SKILL.md              ← Claude reads this to learn what the skill does
├── reference.md          ← Column-alias table, scoring rubric, JSON schemas
├── README.md             ← (this file)
├── scripts/
│   ├── parse_input.py    ← normalize a CSV/TSV/XLSX/JSON into records
│   ├── build_board.py    ← inject classified items into the HTML template
│   └── make_demo.py      ← regenerates the captioned MP4/GIF demo
├── templates/
│   └── board_template.html  ← the single-file board (CSS + JS inline)
└── examples/
    ├── README.md            ← what each card in smoke-test.json exercises
    └── smoke-test.json      ← deliberate exercise of WIP cap, aging, float estimate, today-due
```

---

## Regenerating the demo

```bash
# build the smoke board first (make_demo.py expects /tmp/pb_smoke.html)
python3 scripts/build_board.py \
  --data examples/smoke-test.json \
  --title "Smoke Test Board" \
  --out /tmp/pb_smoke.html

python3 scripts/make_demo.py
# → priority-board-demo.mp4  +  priority-board-demo.gif
# written to the OUT_DIR at the top of make_demo.py
```

Storyboard is action-first: opens with a card mid-drag (Now → Cut), drops it,
then walks through layout / filters / bulk select / inline edit / aging. The
`HOLD` and `FADE` knobs at the top of `make_demo.py` let you retune pacing.

Requires `ffmpeg` and Google Chrome (headless) on macOS.

---

## License

[MIT](../LICENSE) © Ashwin Sinha
