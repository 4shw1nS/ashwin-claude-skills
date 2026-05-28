#!/usr/bin/env python3
"""
build_board.py — inject classified cards into board_template.html.

Takes the lane-assigned items produced by Claude (see reference.md for the
items schema) and writes a single self-contained HTML priority board. The data
is embedded inside <script id="board-data" type="application/json"> by replacing
the literal token __BOARD_DATA__, so there is no JS-string escaping to worry
about (only "<" is escaped to keep the JSON from closing the <script> tag).

Usage:
    python3 build_board.py --data items.json --title "Q3 Reprioritization" \
        --out ~/Desktop/priority-board.html

`items.json` may be either:
  * a bare list of card objects, or
  * an object: {"title":..., "lanes":[...], "cards":[...]}

Each card: {id, lane, order?, title, description?, priority?, status?,
            estimate?, labels?, assignee?, due?, url?, rationale?, extra?}
lane must be one of: now | next | later | cut (default "later" if missing).
"""
import argparse
import datetime
import json
import os
import re
import sys

DEFAULT_LANES = [
    {"id": "now", "name": "Now"},
    {"id": "next", "name": "Next"},
    {"id": "later", "name": "Later"},
    {"id": "cut", "name": "Cut"},
]
LANE_IDS = [l["id"] for l in DEFAULT_LANES]
# Replace the exact data <script> element, not the bare token — the token also
# appears in an HTML comment and a JS fallback check, which must be left intact.
PLACEHOLDER = '<script id="board-data" type="application/json">__BOARD_DATA__</script>'
HERE = os.path.dirname(os.path.abspath(__file__))


def load_items(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        cards = data.get("cards") or data.get("records") or data.get("items") or []
        lanes = data.get("lanes") or DEFAULT_LANES
        title = data.get("title")
    elif isinstance(data, list):
        cards, lanes, title = data, DEFAULT_LANES, None
    else:
        raise ValueError("items file must be a list or an object with a 'cards' list.")
    return cards, lanes, title


def clean_card(c, i):
    if not isinstance(c, dict):
        c = {"title": str(c)}
    lane = str(c.get("lane", "later")).strip().lower()
    if lane not in LANE_IDS:
        # tolerate names like "Now"
        lane = {"now": "now", "next": "next", "later": "later", "cut": "cut"}.get(lane, "later")
    labels = c.get("labels", [])
    if isinstance(labels, str):
        labels = [t.strip() for t in re.split(r"[,;|]", labels) if t.strip()]
    out = {
        "id": str(c.get("id") or "C-%d" % (i + 1)),
        "lane": lane,
        "title": str(c.get("title") or "(untitled)"),
    }
    if "order" in c and c["order"] is not None:
        try:
            out["order"] = float(c["order"])
        except (TypeError, ValueError):
            pass
    for k in ("description", "priority", "status", "assignee", "due", "url", "rationale", "enteredLaneAt"):
        v = c.get(k)
        if v not in (None, ""):
            out[k] = str(v)
    est = c.get("estimate")
    if est not in (None, ""):
        try:
            f = float(est)
            out["estimate"] = int(f) if f == int(f) else f
        except (TypeError, ValueError):
            out["estimate"] = str(est)
    if labels:
        out["labels"] = [str(x) for x in labels]
    if isinstance(c.get("extra"), dict) and c["extra"]:
        out["extra"] = c["extra"]
    return out


def main():
    ap = argparse.ArgumentParser(description="Build a self-contained HTML priority board from classified items.")
    ap.add_argument("--data", required=True, help="Path to items JSON (cards with lane assignments)")
    ap.add_argument("--template", default=os.path.join(HERE, "board_template.html"))
    ap.add_argument("--title", default=None, help="Board title (overrides title in --data)")
    ap.add_argument("--board-id", default=None, help="localStorage namespace id (default: derived from title+date)")
    ap.add_argument("--out", required=True, help="Output .html path")
    args = ap.parse_args()

    if not os.path.exists(args.template):
        sys.exit("Template not found: %s" % args.template)
    if not os.path.exists(args.data):
        sys.exit("Data file not found: %s" % args.data)

    cards_in, lanes, title_in = load_items(args.data)
    cards = [clean_card(c, i) for i, c in enumerate(cards_in)]

    # Stable ordering: by lane sequence, then by `order` if present, else input order.
    lane_rank = {lid: i for i, lid in enumerate(LANE_IDS)}
    for i, c in enumerate(cards):
        c["_seq"] = i
    cards.sort(key=lambda c: (lane_rank.get(c["lane"], 99),
                              c.get("order", c["_seq"]),
                              c["_seq"]))
    for c in cards:
        c.pop("_seq", None)
        c.pop("order", None)  # runtime uses array order; drop to keep file lean

    title = args.title or title_in or "Priority Board"
    stamp = datetime.date.today().isoformat()
    board_id = args.board_id or ("board-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:32] + "-" + stamp)

    # normalize lanes — only title-case when the name was defaulted from the id,
    # so user-renamed lanes (e.g. "URGENT NOW", "in-progress") survive a rebuild.
    # Preserve optional fields like wipLimit so input can pre-set WIP caps.
    norm_lanes = []
    for l in (lanes or DEFAULT_LANES):
        if isinstance(l, dict) and l.get("id"):
            name = l.get("name")
            lane = {
                "id": str(l["id"]),
                "name": str(name) if name else str(l["id"]).title(),
            }
            wip = l.get("wipLimit")
            if wip not in (None, ""):
                try:
                    v = int(wip)
                    if v > 0:
                        lane["wipLimit"] = v
                except (TypeError, ValueError):
                    pass
            norm_lanes.append(lane)
    if not norm_lanes:
        norm_lanes = list(DEFAULT_LANES)

    state = {
        "version": 1,
        "boardId": board_id,
        "title": title,
        "lanes": norm_lanes,
        "cards": cards,
        "updatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    # Escape "<" so the JSON can't terminate the <script> block; this is valid JSON.
    payload = json.dumps(state, ensure_ascii=False).replace("<", "\\u003c")

    with open(args.template, "r", encoding="utf-8") as f:
        html = f.read()
    if PLACEHOLDER not in html:
        sys.exit("Template is missing the board-data placeholder script element.")
    filled = '<script id="board-data" type="application/json">' + payload + "</script>"
    html = html.replace(PLACEHOLDER, filled, 1)

    out_path = os.path.expanduser(args.out)
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    counts = {lid: sum(1 for c in cards if c["lane"] == lid) for lid in LANE_IDS}
    summary = "  ".join("%s:%d" % (lid.capitalize(), counts[lid]) for lid in LANE_IDS)
    sys.stderr.write("Built %d cards (%s)\n-> %s\n" % (len(cards), summary, out_path))


if __name__ == "__main__":
    main()
