# priority-board-html — reference

The knowledge base for turning a list into a pre-sorted Now/Next/Later/Cut
board. Read this before classifying. It defines (1) how columns are recognized,
(2) how to guess each item's lane, and (3) the exact JSON schemas the scripts
expect.

---

## 1. Column aliases

`parse_input.py` maps source headers to these canonical fields (case- and
symbol-insensitive; e.g. `Issue Title`, `issue_title`, `ISSUETITLE` all match
`title`). Use the same mapping when you parse a pasted list/markdown by hand.

| canonical     | matches headers like |
|---------------|----------------------|
| `id`          | id, key, identifier, ticket, issue, issue key, number, ref |
| `title`       | title, name, summary, issue title, task, item, subject |
| `description` | description, desc, details, body, notes, content |
| `priority`    | priority, urgency, prio, p, importance, severity |
| `status`      | status, state, workflow state, stage, column |
| `estimate`    | estimate, points, story points, effort, sp, size, complexity |
| `labels`      | labels, label, tags, tag, categories, type (split on `, ; |`) |
| `assignee`    | assignee, owner, assigned to, responsible, lead |
| `due`         | due, due date, target date, deadline, date, eta |
| `project`     | project, team, cycle, milestone, epic, sprint |
| `url`         | url, link, href, permalink, web url |

Anything unmatched is preserved under each record's `extra` object (still shown
on the card and saved). If `id` is absent, a synthetic `ROW-n` id is assigned.

---

## 2. Lane definitions

| lane    | meaning |
|---------|---------|
| **Now**   | Do immediately / actively committed this cycle. Keep this list realistically short. |
| **Next**  | Queued right after Now — clear value, ready, but not started. |
| **Later** | Backlog / someday — valid but not soon; revisit later. |
| **Cut**   | Won't do — drop, decline, duplicate, obsolete, or already canceled. |

---

## 3. Pre-sort rubric (the four signals)

Score each item, then map the score to a lane. This is a *best guess* the user
will adjust by dragging — bias toward a sensible, defensible split, not false
precision. Always set a one-line `rationale` naming the dominant signal.

Start at **0** and combine:

**a) Priority** (primary driver)
| value | points |
|-------|-------|
| Urgent / P0 / Critical | +4 |
| High / P1 | +3 |
| Medium / P2 / Normal | +1 |
| Low / P3 / Minor | −1 |
| None / blank | 0 |

**b) Status / state**
- In Progress / Started / Doing → **+3** (already underway ⇒ usually Now).
- In Review / Blocked → +2 (in flight; Now/Next).
- Todo / Ready / Selected → +1.
- Backlog / Triage / Icebox → −1.
- Done / Completed / Shipped → route to **Cut** (or omit — ask the user) since it isn't future work.
- Canceled / Won't do / Duplicate / Obsolete → force **Cut**.

**c) Estimate & due date**
- Due date overdue or within ~7 days → **+3**; within ~30 days → +1.
- No due date → 0.
- Estimate is a tie-breaker, not a driver: very large effort (e.g. ≥8 pts / "XL")
  with only medium priority → nudge **−1** (push later); tiny quick wins
  (≤1 pt) with real value → nudge **+1**.

**d) Labels & keywords** (scan labels + title + description)
- Now-pull (**+2** each, cap +3): `security`, `vuln`, `P0`, `sev1`, `outage`,
  `incident`, `blocker`, `blocking`, `regression`, `data loss`, `customer`,
  `urgent`, `hotfix`, `compliance`, `deadline`.
- Bug signal: `bug`, `broken`, `crash`, `error` → +1 (more if also high priority).
- Cut-pull (**−3** each): `wontfix`, `won't fix`, `duplicate`, `obsolete`,
  `deprecated`, `canceled`, `invalid`, `stale`, `someday`, `nice to have`,
  `nice-to-have`, `idea`, `parking lot`, `low-hanging` (only if also low pri).

**Map score → lane**
| score | lane |
|-------|------|
| ≥ 6 | Now |
| 3–5 | Next |
| 0–2 | Later |
| < 0 | Cut |

**Overrides (apply after scoring):**
- Any hard Cut signal (Canceled/Won't do/Duplicate/Obsolete status or cut-pull
  keyword) → **Cut**, regardless of score.
- In Progress + not a Cut signal → at least **Next**, usually **Now**.

**Capacity heuristic:** Now should feel like a committed short list. If scoring
floods Now (say >35–40% of items), keep only the strongest there (highest
score, then nearest due date, then in-progress) and move the rest to Next. State
this in your summary so the user knows it was a deliberate trim.

**Ordering within a lane:** higher score first; tie-break by due date (soonest
first), then by priority, then original order. Emit this as the `order` field
(ascending = appears higher in the lane).

**Tie-breakers between two lanes:** prefer the *lower-commitment* lane (Next over
Now, Later over Next) unless an in-progress status or near due date argues up.

---

## 4. items.json — what you write for build_board.py

A list of cards, or an object with `title`/`lanes`/`cards`. Minimum per card is
`title`; include everything you have. `lane` ∈ `now|next|later|cut`.

```json
{
  "title": "Q3 Reprioritization",
  "cards": [
    {
      "id": "LIN-412",
      "lane": "now",
      "order": 0,
      "title": "Fix checkout 500 on Safari",
      "description": "Customers can't pay; started yesterday.",
      "priority": "Urgent",
      "status": "In Progress",
      "estimate": 3,
      "labels": ["bug", "customer", "payments"],
      "assignee": "Priya",
      "due": "2026-05-27",
      "url": "https://linear.app/acme/issue/LIN-412",
      "rationale": "Urgent customer-facing bug, already in progress."
    }
  ]
}
```

- `order`: number, ascending within the lane (build script sorts by it, then
  drops it — runtime tracks order by array position).
- `due`: ISO `YYYY-MM-DD` so the card's overdue highlight works.
- `estimate`: number (rendered as "N pts"). Strings are tolerated.
- Unknown fields you want to keep → nest under `extra: { ... }`.

---

## 5. Board state schema (what lives in the HTML)

`build_board.py` embeds this inside `<script id="board-data">`. The same shape is
what **Save JSON** exports and **Load JSON** imports, so a saved state file can
be fed straight back into `parse_input.py`/`build_board.py` or shared.

```json
{
  "version": 1,
  "boardId": "board-q3-reprioritization-2026-05-24",
  "title": "Q3 Reprioritization",
  "lanes": [
    {"id":"now","name":"Now"},{"id":"next","name":"Next"},
    {"id":"later","name":"Later"},{"id":"cut","name":"Cut"}
  ],
  "cards": [ { "id":"LIN-412","lane":"now","title":"...","priority":"Urgent",
               "status":"In Progress","estimate":3,"labels":["bug"],
               "assignee":"Priya","due":"2026-05-27","url":"...",
               "rationale":"...","description":"...","extra":{} } ],
  "updatedAt": "2026-05-24T16:30:00"
}
```

- `boardId` namespaces `localStorage` so multiple boards don't collide (and so
  the `null`-origin used on `file://` doesn't mix boards together).
- Lanes are data, so renaming a lane in the UI just edits `lanes[].name`; the
  four ids stay `now/next/later/cut`.
