# ashwin-claude-skills

A personal collection of [Claude Code](https://claude.com/claude-code) skills.

A *skill* is a folder containing a `SKILL.md` (instructions plus a trigger
description) and any helper scripts, templates, or reference docs. Claude Code
auto-loads skills from `~/.claude/skills/` and you can invoke one explicitly by
typing `/<skill-name>`.

This repo is rooted at `~/.claude/skills/`, so the skills here are the live ones
Claude Code runs — no separate install/build step on this machine.

## Skills

### [priority-board-html](priority-board-html/)
Turn a spreadsheet, Google Sheet, Linear/Jira export, pasted list, or JSON into
a single **self-contained HTML drag-and-drop priority board** with Now / Next /
Later / Cut swim lanes. Cards are pre-sorted by best guess, drag on desktop and
touch, auto-save to `localStorage`, and can be saved to / loaded from file.
Bundles a parser (`parse_input.py`), a builder (`build_board.py`), the board
template (`board_template.html`), and the scoring rubric (`reference.md`).

### [linkedin-image-merge](linkedin-image-merge/)
Merge two images side-by-side into a **LinkedIn-ready post**. Each image gets
exactly half the canvas, is resized (never cropped) to fit, and any leftover
space is filled with a blurred extension of that same image. Bundles
`merge_images.py` (Pillow).

## Using a skill on another machine

```bash
git clone https://github.com/4shw1nS/ashwin-claude-skills.git
cp -R ashwin-claude-skills/priority-board-html ~/.claude/skills/
# then in Claude Code: /priority-board-html
```

## Not in this repo

Skills produced by the **skill-generator** meta-skill — `skill-generator`,
`ddia-system-design`, `stock-picks-bg` — live in
[claude-skill-generator](https://github.com/4shw1nS/claude-skill-generator).
`ipl-fantasy` is intentionally excluded for now.
