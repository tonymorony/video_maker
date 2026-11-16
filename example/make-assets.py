#!/usr/bin/env python3
"""Draws the example's stand-in footage: a title card, a tall page and a 6-second recording."""
import os, subprocess
from PIL import Image, ImageDraw

here = os.path.dirname(os.path.abspath(__file__))
card = Image.new("RGB", (1920, 1080), (29, 24, 56))
ImageDraw.Draw(card).rectangle((160, 440, 1760, 640), fill=(246, 244, 249))
card.save(f"{here}/title.png")
page = Image.new("RGB", (1920, 2400), (246, 244, 249))
d = ImageDraw.Draw(page)
for y in range(0, 2400, 200):
    d.rectangle((120, y + 40, 1800, y + 160), fill=(29 + y // 12, 24, 56))
page.save(f"{here}/page.png")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=2560x1440:rate=60:duration=6",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", f"{here}/recording.mp4"], check=True)
