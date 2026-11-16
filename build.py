#!/usr/bin/env python3
"""Builds a narrated video from scenes.json: build.py <project dir>.

Each scene is one spoken line and the footage it plays over. The line's length decides the scene's
length: longer footage is cut, shorter footage holds its last frame. Writes, into <project>/out/:
<name>-voiceover.mp4, <name>.mp4 (the same cut, silent) and <name>-script.txt (lines with timecodes).
See README.md for the scenes.json format."""
import hashlib, json, os, subprocess, sys

P = os.path.abspath(sys.argv[1])
KIT = os.path.dirname(os.path.abspath(__file__))
TTS = os.path.expanduser(os.environ.get("KOKORO_HOME", "~/.cache/kokoro-tts"))
cfg = json.load(open(f"{P}/scenes.json"))
NAME = cfg.get("name", os.path.basename(P))
VOICE, SPEED = cfg.get("voice", "af_heart"), float(cfg.get("speed", 1.0))
LEAD, TAIL = cfg.get("lead", 0.35), cfg.get("tail", 0.75)  # silence before and after each line
W, H = 1920, 1080
FIT = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
       "-video_track_timescale", "15360", "-an"]
OUT, VO, SEG = f"{P}/out", f"{P}/out/vo", f"{P}/out/seg"
for d in (VO, SEG):
    os.makedirs(d, exist_ok=True)


def run(args):
    # -nostdin: without it a backgrounded ffmpeg waits on the terminal and hangs.
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *args], check=True)


def length(path):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        stdin=subprocess.DEVNULL))


def digest(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12]


def spoken(text):
    """The text as the synthesizer gets it: `spell` swaps in spellings it pronounces right."""
    for word, sound in cfg.get("spell", {}).items():
        text = text.replace(word, sound)
    return text


def wav(text):
    return f"{VO}/{digest(VOICE, SPEED, spoken(text))}.wav"


def piece(spec):
    """One piece of footage, encoded alone to 1920x1080 at 30 fps; cached by its spec."""
    out = f"{SEG}/p{digest(spec)}.mp4"
    if os.path.exists(out):
        return out
    if "clip" in spec:  # a stretch of a recording: from, to, optional speed and crop=w:h:x:y
        crop = f"crop={spec['crop']}," if spec.get("crop") else ""
        run(["-ss", str(spec["from"]), "-to", str(spec["to"]), "-i", f"{P}/{spec['clip']}",
             "-vf", f"{crop}setpts=PTS/{spec.get('speed', 1.0)},fps=30,{FIT}", *ENC, out])
    elif "card" in spec:  # a still image, shown `for` seconds
        run(["-loop", "1", "-framerate", "30", "-t", str(spec.get("for", 1.0)), "-i", f"{P}/{spec['card']}",
             "-vf", f"{FIT},format=yuv420p", *ENC, out])
    elif "pan" in spec:  # an eased scroll down a tall screenshot: stops are "y:hold[:move]"
        subprocess.run([sys.executable, f"{KIT}/pan.py", f"{P}/{spec['pan']}", out, *spec["stops"]],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        sys.exit(f"unknown piece: {spec}")
    return out


# 1. Speak every missing line in one run: loading the model takes longer than a line.
scenes = cfg["scenes"]
jobs = [{"text": spoken(s["say"]), "voice": VOICE, "speed": SPEED, "out": wav(s["say"]).replace(".wav", ".raw.wav")}
        for s in scenes if not os.path.exists(wav(s["say"]))]
if jobs:
    json.dump(jobs, open(f"{VO}/jobs.json", "w"))
    subprocess.run([f"{TTS}/venv/bin/python", f"{TTS}/tts.py", f"{VO}/jobs.json"], check=True)
    trim = "silenceremove=start_periods=1:start_threshold=-45dB,areverse"
    for job in jobs:
        # Trim the model's leading and trailing silence, so lines sit where the cut puts them.
        run(["-i", job["out"], "-af", f"{trim},{trim}", "-ar", "48000", "-ac", "1", job["out"].replace(".raw.wav", ".wav")])

# 2. Fit each scene's footage to its line.
parts, lines, sheet, t = [], [], [], 0.0
for i, s in enumerate(scenes):
    first, last = i == 0, i == len(scenes) - 1
    target = LEAD + length(wav(s["say"])) + TAIL + (0.6 if last else 0.0)
    files = [piece(spec) for spec in s["show"]]
    listing = f"{SEG}/{s['id']}.txt"
    open(listing, "w").write("".join(f"file '{f}'\n" for f in files))
    joined = f"{SEG}/{s['id']}-joined.mp4"
    run(["-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", joined])
    footage = length(joined)
    fade = ",fade=t=in:st=0:d=0.5" if first else (f",fade=t=out:st={target - 1.0:.2f}:d=1.0" if last else "")
    out = f"{SEG}/{s['id']}.mp4"
    run(["-i", joined, "-vf", f"tpad=stop_mode=clone:stop_duration={max(0.0, target - footage):.3f}{fade}",
         "-t", f"{target:.3f}", *ENC, out])
    note = "held" if footage < target - 0.05 else ("cut" if footage > target + 0.05 else "fits")
    print(f"{s['id']}: line {target:5.1f}s, footage {footage:5.1f}s, {note} {abs(target - footage):4.1f}s", flush=True)
    parts.append(out)
    lines.append((t + LEAD, wav(s["say"])))
    sheet.append(f"{int(t + LEAD) // 60}:{(t + LEAD) % 60:04.1f}  {s['id']}  {s['say']}")
    t += target

# 3. Join the scenes, then lay each line at its start time.
listing = f"{SEG}/all.txt"
open(listing, "w").write("".join(f"file '{p}'\n" for p in parts))
silent, voiced = f"{OUT}/{NAME}.mp4", f"{OUT}/{NAME}-voiceover.mp4"
run(["-f", "concat", "-safe", "0", "-i", listing, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
     "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", silent])
inputs, chains = [], []
for n, (at, f) in enumerate(lines):
    inputs += ["-i", f]
    chains.append(f"[{n + 1}:a]aresample=48000,adelay={int(at * 1000)}:all=1,apad[a{n}]")
mix = ";".join(chains) + ";" + "".join(f"[a{n}]" for n in range(len(lines)))
mix += f"amix=inputs={len(lines)}:normalize=0:duration=longest,atrim=0:{t:.3f},loudnorm=I=-16:TP=-1.5[a]"
run(["-i", silent, *inputs, "-filter_complex", mix, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
     "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", voiced])
open(f"{OUT}/{NAME}-script.txt", "w").write("\n".join(sheet) + "\n")
print(f"wrote {voiced} and {silent}: {int(t) // 60}:{t % 60:04.1f}")
