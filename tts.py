#!/usr/bin/env python3
"""Speaks lines with Kokoro: tts.py <jobs.json>, a list of {"text", "voice", "speed", "out"}; writes 24 kHz WAVs.

Lives beside kokoro-v1.0.onnx and voices-v1.0.bin; run it with the venv that has kokoro-onnx (setup.sh)."""
import json, os, sys
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
kokoro = Kokoro(f"{HERE}/kokoro-v1.0.onnx", f"{HERE}/voices-v1.0.bin")
for job in json.load(open(sys.argv[1])):
    lang = "en-gb" if job["voice"][0] == "b" else "en-us"
    samples, rate = kokoro.create(job["text"], voice=job["voice"], speed=job.get("speed", 1.0), lang=lang)
    sf.write(job["out"], samples, rate)
    print(f"{len(samples) / rate:5.1f}s {job['voice']} {job['text'][:60]}", flush=True)
