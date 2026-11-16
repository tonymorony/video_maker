#!/usr/bin/env bash
# Installs Kokoro text-to-speech into $KOKORO_HOME (default ~/.cache/kokoro-tts): a Python venv
# with kokoro-onnx, the model and the voices (about 600 MB). Skips whatever is already there.
set -euo pipefail

home="${KOKORO_HOME:-$HOME/.cache/kokoro-tts}"
kit="$(cd "$(dirname "$0")" && pwd)"
release="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

mkdir -p "$home"
cd "$home"
if [ ! -x venv/bin/python ]; then
	python3 -m venv venv
	./venv/bin/pip install -q --upgrade pip
	./venv/bin/pip install -q kokoro-onnx soundfile
fi
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
	[ -s "$f" ] || curl -sL --fail -o "$f" "$release/$f"
done
cp "$kit/tts.py" tts.py
./venv/bin/python -c "import kokoro_onnx, soundfile, platform; print('Kokoro ready in $home, Python', platform.machine())"
