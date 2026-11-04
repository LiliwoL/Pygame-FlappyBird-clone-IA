#!/usr/bin/env bash
# Build the game for the web using pygbag.
#
# The finished, static, browser-ready site is written to: build/web/
# You can deploy that folder to any static host (GitHub Pages, Netlify, etc.)
# or serve it locally with:
#
#     python3 -m http.server -d build/web 9000
#
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
VENV="build/pygbag-venv"

if [ ! -d "$VENV" ]; then
  echo ">> creating build venv at $VENV"
  "$PY" -m venv "$VENV"
fi

"$VENV/bin/pip" install --quiet --upgrade pygbag

echo ">> building web app with pygbag..."
# --disable-sound-format-error keeps our synthesized PCM .wav files working
# (pygbag prefers .ogg, but the generated WAVs are standard 16-bit PCM).
"$VENV/bin/python" -m pygbag \
  --build \
  --disable-sound-format-error \
  --app_name "Pygame FlappyBird Clone" \
  --title "Pygame FlappyBird Clone" \
  .

echo
echo ">> done. Static site available in: build/web/"
echo ">> serve locally with:"
echo "   python3 -m http.server -d build/web 9000"
