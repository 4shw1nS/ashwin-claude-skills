---
name: priority-board-html
description: >
  Turn a spreadsheet, Google Sheet, Linear/Jira export, pasted list, or JSON
  into a single self-contained HTML drag-and-drop priority board with Now /
  Next / Later / Cut swim lanes. Cards are pre-sorted by best guess, drag on
  desktop and touch, auto-save to localStorage, and can be saved to / loaded
  from file. Use when the user asks to "reprioritize these tickets", "make a
  drag and drop board", "turn this list/sheet into a priority board",
  "Now/Next/Later/Cut board", "kanban from this spreadsheet", or invokes
  /priority-board-html.
model: opus
---

# priority-board-html

Convert any list of work items into one **self-contained HTML file**: a
drag-and-drop board with four lanes — **Now / Next / Later / Cut** — pre-sorted
by best guess, with persistent storage and save/load to file. The output is a
single `.html` the user double-clicks; no server, no internet, no dependencies.

Pipeline: **parse → classify (you) → build**. Bundled scripts do the parsing and
HTML assembly; you supply the prioritization judgment.

Skill directory (referenced below as `$SKILL`):
`~/.claude/skills/priority-board-html/`

---

## Phase A — Ingest & normalize

Identify the input, then produce normalized records.

- **File** (`.csv`, `.tsv`, `.xlsx`, `.json`): run the parser.
  ```bash
  python3 ~/.claude/skills/priority-board-html/parse_input.py --input "<path>"
  ```
  It prints `{columns_detected, unmapped, count, records}`. For `.xlsx` it
  auto-installs `openpyxl` on first use; add `--sheet <name|index>` to pick a
  sheet. Write records to a file with `--out records.json` if large.
- **Google Sheet**: ask the user to use **File ▸ Download ▸ Comma-separated
  values (.csv)** and share that file, or paste a *published-to-web CSV* link
  (then download it). Don't attempt to scrape a normal share link.
- **Pasted list / markdown table / bullet list**: parse it yourself into the
  same record shape (don't run the script). Map columns using the alias table in
  `reference.md`.

Then **echo what you found**: the detected column mapping and the row count.
Only ask the user to confirm mapping if a field is genuinely ambiguous (e.g. two
columns both look like the title). Otherwise proceed.

## Phase B — Pre-sort (the best guess)

1. Read `~/.claude/skills/priority-board-html/reference.md` for the scoring
   rubric (the four signals: **priority, status, estimate & due date, labels &
   keywords**) and the exact `items.json` schema.
2. Score every item and assign `lane` (`now|next|later|cut`), an `order` within
   the lane, and a one-line `rationale` naming the dominant reason. Respect the
   overrides (Canceled/Won't-do → Cut; In Progress → at least Next) and the
   **capacity heuristic** (keep Now realistically short; if scoring floods Now,
   trim it and say so).
3. Write `items.json` (a `Write` to a temp/working path is fine).
4. **Summarize the split** for the user before building: counts per lane and a
   few notable calls (what landed in Now, what you Cut, anything you trimmed for
   capacity). This is the "best guess" they're reviewing.

## Phase C — Build & deliver

```bash
python3 ~/.claude/skills/priority-board-html/build_board.py \
  --data items.json \
  --title "<board title>" \
  --out "<output dir>/priority-board.html"
```

Default the output next to the user's input (or `~/Desktop/priority-board.html`
if unclear). Then tell the user:

- **Where** the file is and to **double-click to open** it (works offline).
- **How it behaves**: drag the **⠿ handle** to move/reorder cards across lanes
  (works on desktop and touch); changes **auto-save in the browser**; click a
  card to expand its description; pencil to edit, ＋ Card to add (per-lane
  ＋ button in each lane head), search/`/` to filter, **Filters** toggles a
  chip row for priority/assignee/label, **📋 MD** copies the board to clipboard
  as markdown, **💡** hides/shows rationale, 🌓 toggles theme, ↺ Reset restores
  the original.
- **Keyboard**: `/` focus search · `j`/`k` move card focus · `1`–`4` move
  focused card to that lane · `e` edit · `Enter` expand · `Del`/`Backspace`
  delete · `Esc` clear selection · `⌘Z`/`Ctrl-Z` undo (30-step history).
- **Bulk select**: `⇧`+click range-select, `⌘`/`Ctrl`+click toggle one;
  dragging any selected card moves all selected together.
- **WIP limits**: click a lane's count pill to set a soft WIP cap; the pill
  turns amber at the limit and red over it. You can also pre-seed limits in
  the items JSON: `"lanes":[{"id":"now","name":"Now","wipLimit":5}, ...]`.
- **Aging**: each card tracks when it entered its current lane; after 3 days a
  "🕒 Nd in lane" chip appears, amber after 14d, the card fades after 30d
  (suppressed in Cut).
- **Print**: `Cmd-P` produces a clean printable view (toolbar hidden, lanes
  stacked, all descriptions expanded, no shadows).
- **Durable saves**: **Save HTML** downloads a fresh self-contained file with
  the current board baked in (reopens anywhere exactly as saved); **JSON**
  exports a re-importable state file; **Load** restores from one.
- Note the storage caveat (below) so they know the file saves are the durable
  copy.

Offer to open it: `open "<path>"` (macOS).

---

## Notes & edge cases

- **localStorage on `file://`**: auto-save works in Chrome/Edge but Safari often
  blocks storage for files opened directly. The board detects this and shows a
  banner steering the user to **Save HTML / JSON**, which are the durable record.
  For rock-solid auto-save, the user can serve the folder
  (`python3 -m http.server`) and open via `http://localhost`.
- **Lanes are fixed** to Now/Next/Later/Cut by design, but their names are
  editable in the UI (the ids stay the same). Don't add/remove lanes.
- **No internet / no CDN**: everything (CSS, JS, icons) is inline. Keep it that
  way — never add external `<script>`/`<link>` to the template.
- **Done/Completed items**: these aren't future work. Default to **Cut** (or ask
  whether to exclude them) rather than cluttering Now/Next.
- **Big lists**: the board handles a few hundred cards fine. For thousands,
  suggest filtering the source first.
- **Re-running**: feeding a previously exported state JSON back through
  `build_board.py --data state.json` rebuilds the board (useful for restyling or
  re-titling). Don't feed a state JSON through `parse_input.py` — it only knows
  the canonical input aliases, so `lane`/`rationale`/`order` would be dropped
  into `extra` and the lane assignments lost.

## When NOT to use

- The user wants live two-way sync with Linear/Jira/Sheets — this produces a
  static, offline snapshot, not a connected app.
- The user wants a server-backed multi-user board, auth, or real-time
  collaboration. This is single-file and local.
