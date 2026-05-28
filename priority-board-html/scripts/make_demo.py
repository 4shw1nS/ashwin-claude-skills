#!/usr/bin/env python3
"""Generate a demo MP4 (+ fallback GIF) for priority-board-html.

Storyboard is action-first: open with a card mid-drag from Now → Cut, then drop
it and show the WIP counter flip from 3/2 (red) to 2/2 (amber). Only after that
do we show the static board and the rest of the features. The xfade durations
are per-frame so the drag sequence uses near-hard cuts (motion feel) while
scene transitions get the longer crossfade.

Each frame is one screenshot of the smoke-test HTML, with a small <script>
appended that puts the page into that state plus a fixed-position caption.
"""
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------- paths ----------
BASE = Path("/tmp/pb_smoke.html")
WORK = Path("/tmp/pb_demo")
OUT_DIR = Path("/Users/ashwinsinha/Desktop/Root/Ashwin/Engg/Claude")
OUT_MP4 = OUT_DIR / "priority-board-demo.mp4"   # primary
OUT_GIF = OUT_DIR / "priority-board-demo.gif"   # fallback

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH, HEIGHT = 1500, 900

MP4_WIDTH = 1400
MP4_FPS = 24
GIF_WIDTH = 1000
GIF_FPS = 12

DEFAULT_HOLD = 2.8     # static-feature scenes
DEFAULT_FADE = 0.45    # scene→scene crossfade
MOTION_FADE = 0.08     # near-hard cut between motion sub-frames

# ---------- caption styling (vertically slightly below center) ----------
CAPTION_CSS = """
<style>
  .demo-caption{
    position:fixed; top:60%; left:50%; transform:translate(-50%,-50%);
    z-index:9999; max-width:min(880px, 78vw);
    background:rgba(15,18,23,0.92);
    border:1px solid rgba(165,180,252,0.35);
    box-shadow:0 24px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.4);
    color:#fff; padding:22px 34px; border-radius:18px; text-align:center;
    font:600 28px/1.32 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    letter-spacing:.005em; pointer-events:none;
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
  }
  .demo-caption .step{
    display:block; font-size:11px; font-weight:700; letter-spacing:.18em;
    text-transform:uppercase; color:#a5b4fc; margin:0 0 10px;
  }
</style>
"""

# ---------- per-frame setup scripts ----------

# Mid-flight: T-3 lifted from Now, ghost positioned between Now and Cut,
# Cut lane shows the drop-active outline + a placeholder where it will land.
DRAG_FLIGHT_JS = r"""
(function(){
  var src = document.querySelector('.card[data-card-id="T-3"]');
  if (!src) return;
  var rect = src.getBoundingClientRect();
  src.classList.add('source-hidden');
  // Placeholder in Now where T-3 was
  var nowCards = document.querySelector('.lane[data-lane="now"] .lane-cards');
  var ph1 = document.createElement('div');
  ph1.className = 'drop-placeholder';
  ph1.style.height = rect.height + 'px';
  nowCards.appendChild(ph1);
  // The floating drag ghost — same card, rotated, mid-flight
  var ghost = src.cloneNode(true);
  ghost.classList.remove('source-hidden','dim','expanded','selected');
  ghost.classList.add('drag-ghost');
  ghost.style.width = rect.width + 'px';
  ghost.style.left = '780px';
  ghost.style.top  = '240px';
  document.body.appendChild(ghost);
  // Cut highlighted as the drop target
  var cutLane = document.querySelector('.lane[data-lane="cut"]');
  cutLane.classList.add('drop-active');
  var cutCards = cutLane.querySelector('.lane-cards');
  var hint = cutCards.querySelector('.empty-hint');
  if (hint) hint.remove();
  var ph2 = document.createElement('div');
  ph2.className = 'drop-placeholder';
  ph2.style.height = rect.height + 'px';
  cutCards.insertBefore(ph2, cutCards.firstChild);
})();
""".strip()

# Landed: T-3 actually in Cut. WIP pill flips 3/2 (red) → 2/2 (amber) with a
# small scale+glow pulse so the change is impossible to miss.
DRAG_LANDED_JS = r"""
(function(){
  var src = document.querySelector('.card[data-card-id="T-3"]');
  var cutCards = document.querySelector('.lane[data-lane="cut"] .lane-cards');
  if (src && cutCards) {
    src.classList.remove('source-hidden');
    cutCards.insertBefore(src, cutCards.firstChild);
  }
  var nowCnt = document.querySelector('[data-lane-cnt="now"]');
  if (nowCnt) {
    nowCnt.textContent = '2/2';
    nowCnt.classList.remove('over-limit');
    nowCnt.classList.add('at-limit');
    nowCnt.style.transform = 'scale(1.25)';
    nowCnt.style.boxShadow = '0 0 0 5px rgba(245,158,11,0.45), 0 0 24px rgba(245,158,11,0.6)';
    nowCnt.style.fontWeight = '700';
  }
  var nowSum = document.querySelector('.lane[data-lane="now"] .lane-meta .sum');
  if (nowSum) nowSum.textContent = 'Σ 5';
  var cutCnt = document.querySelector('[data-lane-cnt="cut"]');
  if (cutCnt) cutCnt.textContent = '2';
  document.querySelectorAll('.drop-placeholder').forEach(function(p){ p.remove(); });
  document.querySelectorAll('.lane.drop-active').forEach(function(l){ l.classList.remove('drop-active'); });
  document.querySelectorAll('.empty-hint').forEach(function(h){ h.remove(); });
})();
""".strip()

FILTERS_JS = r"""
document.getElementById('btn-filters').click();
setTimeout(function(){
  document.querySelectorAll('.filter-chip').forEach(function(c){
    if (c.dataset.filterVal==='Urgent' || c.dataset.filterVal==='High' || c.dataset.filterVal==='Priya') c.click();
  });
}, 60);
""".strip()

BULK_JS = r"""
['T-1','T-2','T-3'].forEach(function(id){
  var el=document.querySelector('.card[data-card-id="'+id+'"]');
  if (el) el.classList.add('selected');
});
document.getElementById('selection-count').textContent='3 selected';
document.getElementById('selection-bar').classList.add('show');
""".strip()

EDIT_JS = r"""
var c=document.querySelector('.card[data-card-id="T-2"] .edit');
if (c) c.click();
""".strip()

# Aging: glow the T-7 card to draw the eye to its "23d in lane" chip.
AGING_JS = r"""
(function(){
  var card = document.querySelector('.card[data-card-id="T-7"]');
  if (!card) return;
  card.style.boxShadow = '0 0 0 3px rgba(245,158,11,0.7), 0 14px 32px rgba(0,0,0,0.55)';
  card.style.transform = 'translateY(-2px)';
  var chip = card.querySelector('.chip.age');
  if (chip) {
    chip.style.transform = 'scale(1.18)';
    chip.style.boxShadow = '0 0 0 3px rgba(245,158,11,0.45)';
  }
})();
""".strip()


# ---------- storyboard ----------
@dataclass
class F:
    slug: str
    caption: str
    setup: str = ""
    hold: float = DEFAULT_HOLD
    fade_in: float = DEFAULT_FADE   # crossfade FROM previous frame


FRAMES = [
    # Scene 1: action (drag a card live)
    F("01-before", "Live drag-drop reprioritization",
      "", hold=1.4, fade_in=DEFAULT_FADE),
    F("02-flight", "Live drag-drop reprioritization",
      DRAG_FLIGHT_JS, hold=0.55, fade_in=MOTION_FADE),
    F("03-landed", "WIP updates live · 3/2 → 2/2",
      DRAG_LANDED_JS, hold=2.6, fade_in=MOTION_FADE),
    # Scene 2: it's a real generated board
    F("04-overview", "Custom board, generated with Claude",
      "", hold=2.8),
    # Scene 3+: features at a glance
    F("05-filters", "Slice by priority, owner, or label",
      FILTERS_JS, hold=2.6),
    F("06-bulk",    "Move many cards at once",
      BULK_JS, hold=2.6),
    F("07-edit",    "Edit anything inline",
      EDIT_JS, hold=2.6),
    F("08-aging",   "Stale work surfaces itself",
      AGING_JS, hold=2.6),
]


# ---------- frame builder ----------
def build_frame_html(frame: F, step_label: str) -> Path:
    html = BASE.read_text()
    # Force dark theme as the default
    html = html.replace('data-theme="light"', 'data-theme="dark"', 1)
    # Clear localStorage so frames don't bleed into each other
    clear = '<script>try{localStorage.clear()}catch(e){}</script>'
    html = html.replace('</head>', clear + CAPTION_CSS + '</head>', 1)
    caption_html = (
        '<div class="demo-caption">'
        f'<span class="step">{step_label}</span>'
        f'{frame.caption}'
        '</div>'
    )
    injection = caption_html
    if frame.setup:
        injection += (
            '<script>window.addEventListener("load",function(){'
            'setTimeout(function(){' + frame.setup + '},150);});</script>'
        )
    html = html.replace('</body>', injection + '</body>', 1)
    target = WORK / f"frame-{frame.slug}.html"
    target.write_text(html)
    return target


def shoot(html_path: Path, png_path: Path) -> None:
    cmd = [
        CHROME, "--headless=new", "--hide-scrollbars",
        "--disable-gpu", "--no-sandbox",
        f"--window-size={WIDTH},{HEIGHT}",
        f"--screenshot={png_path}",
        "--virtual-time-budget=2000",
        html_path.absolute().as_uri(),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if res.returncode != 0 or not png_path.exists():
        sys.stderr.write(f"Chrome failed for {html_path}:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}\n")
        raise SystemExit(1)


# ---------- ffmpeg chain ----------
def _xfade_chain(items, width: int, fps: int):
    """items: list of (png_path, hold_seconds, fade_in_from_previous_seconds).

    Each clip's duration covers its hold + the fade overlap at both ends, so
    visible hold equals the requested `hold`. First and last clips have no
    leading / trailing fade respectively.
    """
    n = len(items)
    durations = []
    for i, (_, hold, fi) in enumerate(items):
        fade_in = fi if i > 0 else 0.0
        fade_out = items[i + 1][2] if i + 1 < n else 0.0
        durations.append(hold + fade_in + fade_out)

    ff_in = []
    for (path, _, _), dur in zip(items, durations):
        ff_in += ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(path)]

    norm = [
        f"[{i}:v]scale={width}:-1:flags=lanczos,format=yuv420p,fps={fps},settb=AVTB[v{i}]"
        for i in range(n)
    ]
    chain = []
    current, cum_dur = "v0", durations[0]
    for i in range(1, n):
        fade = items[i][2]
        offset = cum_dur - fade
        label = f"x{i}"
        chain.append(
            f"[{current}][v{i}]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[{label}]"
        )
        current = label
        cum_dur += durations[i] - fade

    return ff_in, ";".join(norm + chain), current


def build_mp4(labeled_dir: Path, out: Path) -> None:
    pngs = {p.stem.replace("labeled-", ""): p for p in labeled_dir.glob("labeled-*.png")}
    items = [(pngs[f.slug], f.hold, f.fade_in) for f in FRAMES]
    # Append the first frame again at the end so the loop restart is seamless.
    items.append((pngs[FRAMES[0].slug], FRAMES[0].hold, DEFAULT_FADE))

    ff_in, filter_str, final = _xfade_chain(items, MP4_WIDTH, MP4_FPS)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", *ff_in,
        "-filter_complex", filter_str,
        "-map", f"[{final}]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "22", "-preset", "slow",
        "-movflags", "+faststart",
        str(out),
    ], check=True)


def build_gif(mp4: Path, out: Path) -> None:
    """Quantize the MP4 to a looping GIF (fallback artifact for surfaces that
    refuse video). bayer:5 is purely positional dither so identical hold frames
    quantize identically and diff_mode=rectangle can dedup them."""
    palette = out.with_name(out.stem + "-palette.png")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(mp4),
        "-vf", f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette),
    ], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(mp4), "-i", str(palette),
        "-lavfi", (
            f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos[x];"
            "[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
        ),
        "-loop", "0",
        str(out),
    ], check=True)
    palette.unlink(missing_ok=True)


def main() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    for i, fr in enumerate(FRAMES, 1):
        step = f"{i:02d} / {len(FRAMES):02d}"
        html = build_frame_html(fr, step)
        labeled = WORK / f"labeled-{fr.slug}.png"
        shoot(html, labeled)
        print(f"  ✓ {fr.slug}: {labeled.stat().st_size//1024} KB")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_mp4(WORK, OUT_MP4)
    print(f"\nMP4 → {OUT_MP4} ({OUT_MP4.stat().st_size//1024} KB)")
    build_gif(OUT_MP4, OUT_GIF)
    print(f"GIF → {OUT_GIF} ({OUT_GIF.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
