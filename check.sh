#!/usr/bin/env bash
# check.sh <video.mp4> [seconds per tile]: what an agent can verify without ears.
# Prints the streams and length, the loudness and every pause longer than 2.5 s, and writes a contact
# sheet beside the video (<video>-sheet.jpg) to Read: six tiles to a row, and tile k, counted from 0
# along the rows, comes from the N seconds that start at k x N. No timecodes are burnt in:
# Homebrew's ffmpeg has no drawtext filter.
set -euo pipefail

f="$1"
every="${2:-3}"
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate -of compact "$f" </dev/null
ffmpeg -nostdin -hide_banner -i "$f" -vn -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume" || echo "no audio"
echo "pauses longer than 2.5 s (start, length):"
ffmpeg -nostdin -hide_banner -i "$f" -vn -af silencedetect=noise=-40dB:d=2.5 -f null - 2>&1 |
	grep -o "silence_start: [0-9.]*\|silence_duration: [0-9.]*" | paste - - || true
seconds="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" </dev/null)"
rows="$(awk -v s="$seconds" -v e="$every" 'BEGIN { n = int(s / e); if (n < 1) n = 1; print int((n + 5) / 6) }')"
ffmpeg -nostdin -v error -y -i "$f" -frames:v 1 -q:v 4 \
	-vf "fps=1/$every:round=down,scale=480:-2,tile=6x$rows:padding=4:color=red" "${f%.mp4}-sheet.jpg"
echo "sheet: ${f%.mp4}-sheet.jpg ($rows rows of 6, one tile per $every s)"
