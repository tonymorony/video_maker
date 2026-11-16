#!/usr/bin/env python3
"""pan.py <tall.png> <out.mp4> <y:hold[:move]>...  An eased vertical pan over a full-page snapshot.

Each stop scrolls to y (in pixels of the PNG once scaled to 1920 wide) over `move` seconds
(default 1.6), then holds `hold` seconds. The first stop starts there with no move.
Frames are 1920x1080 at 30 fps. Needs Pillow."""
import subprocess, sys
from PIL import Image

W, H, FPS = 1920, 1080, 30
src, out, *stops = sys.argv[1:]
im = Image.open(src).convert("RGB")
if im.width != W:
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
if im.height < H:  # a short page: pad it, so there is a full frame to show
    tall = Image.new("RGB", (W, H), im.getpixel((0, im.height - 1)))
    tall.paste(im, (0, 0))
    im = tall
top = max(0, im.height - H)
ease = lambda t: 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
ys = []
cur = None
for s in stops:
    p = s.split(":")
    y, hold, move = min(top, max(0, int(p[0]))), float(p[1]), float(p[2]) if len(p) > 2 else 1.6
    if cur is not None:
        n = round(move * FPS)
        ys += [cur + (y - cur) * ease(i / n) for i in range(1, n + 1)]
    ys += [y] * round(hold * FPS)
    cur = y
ff = subprocess.Popen(
    ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
     "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
     "-r", str(FPS), "-video_track_timescale", "15360", out],
    stdin=subprocess.PIPE)
for y in ys:
    # Sub-pixel scroll: blend two rows' worth of crop, so slow pans don't step.
    y0 = int(y)
    f = y - y0
    a = im.crop((0, y0, W, y0 + H))
    if f > 0.01 and y0 + 1 + H <= im.height:
        a = Image.blend(a, im.crop((0, y0 + 1, W, y0 + 1 + H)), f)
    ff.stdin.write(a.tobytes())
ff.stdin.close()
ff.wait()
print(f"{out}: {len(ys) / FPS:.1f} s")
