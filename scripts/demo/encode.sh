#!/usr/bin/env bash
# Encode the frames written by record_demo.mjs: OUT_DIR/vigraph-demo.mp4 (H.264, 1920x1200,
# 30 fps) and OUT_DIR/vigraph-demo.gif (960 px wide, 10 fps, for the README).
#   scripts/demo/encode.sh OUT_DIR        (FFMPEG=/path/to/ffmpeg if it is not on PATH)
set -euo pipefail
out="${1:?usage: encode.sh OUT_DIR}"
ffmpeg="${FFMPEG:-ffmpeg}"

"$ffmpeg" -hide_banner -loglevel error -y -f concat -safe 0 -i "$out/frames/frames.txt" \
  -vf "fps=30,scale=1920:1200:flags=lanczos,format=yuv420p" \
  -c:v libx264 -preset slow -crf 20 -movflags +faststart "$out/vigraph-demo.mp4"

"$ffmpeg" -hide_banner -loglevel error -y -i "$out/vigraph-demo.mp4" \
  -vf "fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  "$out/vigraph-demo.gif"

ls -lh "$out/vigraph-demo.mp4" "$out/vigraph-demo.gif"
