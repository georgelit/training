#!/bin/sh
# Пересобирает страницу из свежих данных Garmin и публикует.
set -e
cd "$(dirname "$0")"
PY="$HOME/Documents/Treaning + Claude/garmin-ai/venv/bin/python"
"$PY" tools/build.py
git add -A
git commit -q -m "обновление $(date '+%d.%m %H:%M')" || { echo "изменений нет"; exit 0; }
git push -q
echo "✅ https://georgelit.github.io/training/  (обновится за пару минут)"
