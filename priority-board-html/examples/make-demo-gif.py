#!/usr/bin/env python3
"""Generate a slideshow GIF that demos priority-board-html.

For each frame we take the smoke-test HTML, inject a localStorage-clear
script in <head> (so frames don't bleed into each other), and append a
small setup script before </body> that puts the page into the demo state.
Then we headless-Chrome-screenshot it, label it, and ffmpeg-assemble.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path("/tmp/pb_smoke.html")
WORK = Path("/tmp/pb_demo")
OUT_DIR = Path("/Users/ashwinsinha/Desktop/Root/Ashwin/Engg/Claude")
OUT_MP4 = OUT_DIR / "priority-board-demo.mp4"   # primary — ~10× smaller than GIF
OUT_GIF = OUT_DIR / "priority-board-demo.gif"   # fallback for surfaces that don't accept video

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH, HEIGHT = 1500, 900
SCALE = 1  # device-pixel-ratio for screenshots

# Every frame renders dark — the user explicitly preferred dark mode.
# (slug, caption, setup_js — runs ~150ms after load with full DOM ready)
FRAMES = [
    ("01-default",
     "Pre-sorted Now / Next / Later / Cut · 3/2 over WIP cap · 23d aging chip",
     ""),
    ("02-expanded",
     "Click a card to expand its description",
     "var c=document.querySelector('.card[data-card-id=\"T-1\"]'); if(c){c.classList.add('expanded'); c.scrollIntoView({block:'center'});}"),
    ("03-filters",
     "Filter chips — auto-built from priority, assignee, label",
     "document.getElementById('btn-filters').click();"
     "setTimeout(function(){"
     "  var chips=document.querySelectorAll('.filter-chip');"
     "  chips.forEach(function(c){ if(c.dataset.filterVal==='Urgent' || c.dataset.filterVal==='High' || c.dataset.filterVal==='Priya') c.click(); });"
     "}, 60);"),
    ("04-search",
     "Text search across id / title / description / labels / assignee",
     "var s=document.getElementById('search'); s.value='due'; s.dispatchEvent(new Event('input',{bubbles:true}));"),
    ("05-select",
     "Bulk select: ⇧+click range, ⌘+click toggle — drag any to move all",
     "['T-1','T-2','T-3'].forEach(function(id){ var el=document.querySelector('.card[data-card-id=\"'+id+'\"]'); if(el) el.classList.add('selected'); });"
     "document.getElementById('selection-count').textContent='3 selected';"
     "document.getElementById('selection-bar').classList.add('show');"),
    ("06-rationale",
     "Hide rationale (💡) to declutter cards",
     "document.body.classList.add('hide-rationale');"
     "var b=document.getElementById('btn-rationale'); if(b) b.classList.add('active');"),
    ("07-edit",
     "Inline edit form · ID / lane / priority / due / labels / rationale",
     "var c=document.querySelector('.card[data-card-id=\"T-2\"] .edit'); if(c) c.click();"),
    ("08-wip-amber",
     "WIP limit on Now lowered to 3 → amber 'at limit' pill",
     "var cnt=document.querySelector('[data-lane-cnt=\"now\"]'); if(cnt){ cnt.textContent='3/3'; cnt.classList.remove('over-limit'); cnt.classList.add('at-limit'); cnt.title='WIP limit 3 — click to change'; }"),
]


CAPTION_CSS = """
<style>
  .demo-caption{
    /* sit slightly below the visual center so the native footer (shortcut hints)
       stays visible underneath, and the upper half of the board remains uncovered */
    position:fixed; top:60%; left:50%; transform:translate(-50%,-50%);
    z-index:9999; max-width:min(880px, 78vw);
    background:rgba(15,18,23,0.92);
    border:1px solid rgba(165,180,252,0.35);
    box-shadow:0 24px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.4);
    color:#fff; padding:22px 34px; border-radius:18px; text-align:center;
    font:600 26px/1.32 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    letter-spacing:.005em; pointer-events:none;
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
  }
  .demo-caption .step{
    display:block; font-size:11px; font-weight:700; letter-spacing:.18em;
    text-transform:uppercase; color:#a5b4fc; margin:0 0 10px;
  }
</style>
"""

def build_frame_html(slug: str, caption: str, step_label: str, setup_js: str) -> Path:
    html = BASE.read_text()
    # 0. Force dark theme as the page default. The IIFE only sets the attribute
    #    when localStorage has a value, and we clear localStorage below, so the
    #    HTML attribute is the source of truth here.
    html = html.replace('data-theme="light"', 'data-theme="dark"', 1)
    # 1. Clear localStorage before main IIFE runs (so frames don't bleed into each other)
    clear = '<script>try{localStorage.clear()}catch(e){}</script>'
    html = html.replace('</head>', clear + CAPTION_CSS + '</head>', 1)
    # 2. Append setup script that fires after render, then the caption overlay
    caption_html = (
        '<div class="demo-caption">'
        f'<span class="step">{step_label}</span>'
        f'{caption}'
        '</div>'
    )
    injection = caption_html
    if setup_js:
        injection += (
            '<script>window.addEventListener("load",function(){'
            'setTimeout(function(){' + setup_js + '},150);});</script>'
        )
    html = html.replace('</body>', injection + '</body>', 1)
    target = WORK / f"frame-{slug}.html"
    target.write_text(html)
    return target


def shoot(html_path: Path, png_path: Path) -> None:
    cmd = [
        CHROME,
        "--headless=new",
        "--hide-scrollbars",
        "--disable-gpu",
        "--no-sandbox",
        f"--window-size={WIDTH},{HEIGHT}",
        f"--screenshot={png_path}",
        "--virtual-time-budget=2000",
        "--force-device-scale-factor=" + str(SCALE),
        html_path.absolute().as_uri(),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if res.returncode != 0 or not png_path.exists():
        sys.stderr.write(f"Chrome failed for {html_path}:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}\n")
        raise SystemExit(1)


MP4_WIDTH = 1400
MP4_FPS = 24      # libx264 handles motion+fade beautifully at 24fps
GIF_WIDTH = 1000
GIF_FPS = 12
HOLD = 3.2        # seconds each frame is held statically (long enough to read)
FADE = 0.45       # seconds of crossfade between frames


def _xfade_chain(inputs, width: int, fps: int):
    """Return (ffmpeg input args, filter_complex string, final stream label)."""
    n = len(inputs)
    clip_dur = HOLD + FADE
    ff_in = []
    for f in inputs:
        ff_in += ["-loop", "1", "-t", f"{clip_dur:.3f}", "-i", str(f)]
    norm = [
        f"[{i}:v]scale={width}:-1:flags=lanczos,format=yuv420p,fps={fps},settb=AVTB[v{i}]"
        for i in range(n)
    ]
    chain, cur, cum = [], "v0", clip_dur
    for i in range(1, n):
        off = cum - FADE
        nxt = f"x{i}"
        chain.append(
            f"[{cur}][v{i}]xfade=transition=fade:duration={FADE:.3f}:offset={off:.3f}[{nxt}]"
        )
        cur = nxt
        cum += clip_dur - FADE
    return ff_in, ";".join(norm + chain), cur


def build_mp4(labeled_dir: Path, out: Path) -> None:
    """Crossfade-chain labeled PNGs into a smoothly looping MP4 (h.264).

    Each frame is held HOLD seconds, then crossfades over FADE seconds into the
    next. After the last frame, we crossfade back into frame 1 so the loop
    restart is seamless.
    """
    pngs = sorted(labeled_dir.glob("labeled-*.png"))
    if not pngs:
        raise SystemExit("No labeled frames to assemble.")
    inputs = pngs + [pngs[0]]   # loopback frame for smooth restart
    ff_in, filter_str, final = _xfade_chain(inputs, MP4_WIDTH, MP4_FPS)
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
    refuse video). Uses bayer:5 positional dither so identical "hold" frames
    quantize identically and diff_mode=rectangle can dedup them — sierra2_4a
    is prettier but its error-diffusion state shifts every frame and defeats
    the dedup, ballooning file size."""
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

    for i, (slug, caption, setup) in enumerate(FRAMES, 1):
        step = f"{i:02d} / {len(FRAMES):02d}"
        html = build_frame_html(slug, caption, step, setup)
        # The caption is now baked into the HTML, so the shot itself is the "labeled" image.
        labeled = WORK / f"labeled-{slug}.png"
        shoot(html, labeled)
        print(f"  ✓ {slug}: {labeled.stat().st_size//1024} KB")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_mp4(WORK, OUT_MP4)
    print(f"\nMP4 → {OUT_MP4} ({OUT_MP4.stat().st_size//1024} KB)")
    build_gif(OUT_MP4, OUT_GIF)
    print(f"GIF → {OUT_GIF} ({OUT_GIF.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
