# video_maker: a narrated explainer video from screen footage

You are making a short video (1–3 minutes) in which a synthetic voice explains what the screen shows.
The method is **line-led**: the script is split into lines, one per scene, each line is spoken first,
and the picture is then cut or held to the length of its line. Everything runs on your Mac, with no
cloud service and no key.

The scripts are general: nothing in them is tied to one product or to one set of footage.

## Files

| File | What it does |
|---|---|
| `setup.sh` | Installs Kokoro text-to-speech (venv, model, voices; about 600 MB) into `$KOKORO_HOME` |
| `tts.py` | Speaks a list of lines to WAV files; `setup.sh` copies it beside the model |
| `build.py` | Reads `<project>/scenes.json`, speaks the lines, fits the footage, writes the videos |
| `pan.py` | Turns a tall full-page screenshot into an eased scroll; `build.py` calls it |
| `check.sh` | Reports the streams, loudness and pauses of a video, and writes a contact sheet |
| `example/` | A 13-second smoke test with drawn stand-in footage |

## Steps

1. **Set up.** Run `./setup.sh`, then the smoke test:
   `python3 example/make-assets.py && python3 build.py example`.
   Done when the build prints `wrote … example-voiceover.mp4 and … example.mp4: 0:13.6`.
   It needs `ffmpeg`, and `python3` with Pillow.

2. **Collect the footage** into a new project folder, outside any git repo. Three kinds work:
   - a **clip**: a screen recording (`.mov`, `.mp4`), from the owner or recorded by you;
   - a **pan**: a full-page PNG screenshot, for pages longer than one screen;
   - a **card**: a 1920×1080 PNG for the title and the ending. Draw it as an HTML page in the
     product's own fonts and colors and screenshot it with headless Chrome
     (`--headless=new --window-size=1920,1080 --screenshot=card.png file://…/card.html`).

   Map every recording before you write a word: `./check.sh recording.mov 3`, then Read the sheet.
   Done when you can name, for each thing the video must show, the file and the seconds where it
   happens.

3. **Write the lines.** One line per scene, and each line says what its scene shows.
   - Kokoro speaks about 3 words a second at speed 1.0, so a 2-minute video is about 300 words
     including pauses.
   - State only what the footage or the product proves. A line like "every step is real" needs
     every step on screen to be real.
   - Use the product's own vocabulary, exactly as its docs spell it.

   Done when each line has footage at least as long as the line, and the owner has approved the
   text. Text is cheap to change now and costs a rebuild later.

4. **Write `scenes.json`** in the project folder. Paths are relative to it.

   ```json
   {
     "name": "demo",
     "voice": "af_heart",
     "speed": 1.0,
     "spell": { "API": "A P I", "example.com": "example dot com" },
     "scenes": [
       { "id": "s01", "say": "Title line.", "show": [{ "card": "title.png", "for": 1.0 }] },
       {
         "id": "s02",
         "say": "What happens in this scene.",
         "show": [
           { "clip": "recording.mov", "from": 62.6, "to": 72.4, "speed": 1.3, "crop": "3024:1558:112:250" },
           { "pan": "pr-page.png", "stops": ["0:1.5", "520:3", "980:3:2.0"] }
         ]
       }
     ]
   }
   ```

   - `clip`: seconds `from`–`to` of a recording; `speed` above 1 plays it faster; `crop` is
     `width:height:x:y` in the recording's pixels, to drop the browser's tabs and toolbar.
   - `pan`: each stop is `y:hold[:move]`: scroll to `y` (pixels, after the PNG is scaled to 1920
     wide) over `move` seconds (default 1.6), then stay `hold` seconds. The first stop has no move.
   - `card`: a still for `for` seconds; it is held longer when its line is longer.
   - `spell`: spellings for the synthesizer only. The script file keeps the real text.
   - `lead` and `tail` (default 0.35 and 0.75) are the silence before and after each line.

5. **Build:** `python3 build.py <project>`. It prints one row per scene:

   ```
   s02: line   6.8s, footage   5.9s, held  0.9s
   ```

   `held` means the last frame froze that long; `cut` means that much footage was dropped from the
   end. Done when no scene is held more than about 2 seconds on a moving picture, and nothing that
   the line mentions is cut. Fix a hold by adding footage or shortening the line; fix a cut by
   raising `speed`, tightening `from`/`to`, or lengthening the line.

6. **Check:** `./check.sh <project>/out/<name>-voiceover.mp4 3`, then Read the sheet. Done when:
   - the voiced and the silent file have the same length;
   - the mean volume is near −20 dB and the peak near −1.5 dB;
   - every listed pause is one you intended;
   - against `<name>-script.txt`, each line's timecode lands on the tile that shows what it says.

7. **Hand the sound to the owner.** You cannot hear the result, and a voice that reads well on
   paper can be wrong to the ear. Give them the path to the voiced file and ask about three things: the
   voice, the pronunciation of every name and abbreviation, and the pace. Report which checks from
   step 6 you ran, and say that nobody has listened yet. Done when the owner has listened and
   approved, or you have rebuilt with their corrections.

## Voices

The default is `af_heart` (female, American); keep one voice across videos that belong together.
Others worth a sample: `af_bella`, `am_michael`, `am_fenrir`, `bm_george`, `bf_emma`. A name
starting with `b` is spoken as British English. To offer a choice, speak one 15-second line in each
voice with `tts.py` and give the owner the WAV files.

## What the environment won't tell you

- **macOS `say` is not good enough.** Only compact voices are installed, and they sound
  synthetic next to Kokoro.
- **Homebrew's ffmpeg may have no `drawtext` and no `subtitles` filter.** Put text on screen as a
  PNG: a card, or a transparent band laid over a clip with `overlay`.
- **Kokoro reads abbreviations and domains badly.** Spell them in `spell` the way they sound:
  letters apart for an abbreviation (`A P I`), words for a domain (`example dot com`), `A.I.` for AI.
  Write amounts as words ("two dollars").
- **Spoken lines and encoded pieces are cached** in `<project>/out/vo` and `out/seg`, keyed by their
  text or spec, so a rebuild after one changed line takes seconds. A change to `pan.py` or
  `build.py` does not clear them: delete `out/seg` after one.
- **Speech is slow when the Kokoro venv's Python runs under Rosetta** (x86_64 on an arm64 Mac). The
  three-line example builds in 15–20 seconds; a full video from long retina recordings takes
  minutes, so run that build in the background.
- **Keep the silent cut.** An edited version without the voice is useful as a separate
  file; `build.py` writes both from the same cut, so they match frame for frame.
- **A recording made by an agent must show only pages that are safe to publish.** Steps that need
  the owner's credentials or signature stay with the owner: plan those shots with them.
