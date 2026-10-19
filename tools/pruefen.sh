#!/usr/bin/env bash
# Alle Prüfungen lokal ausführen: bash tools/pruefen.sh
# (dieselben Schritte laufen bei jedem Pull Request auf GitHub)
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

echo "== Selbsttest der Werkzeuge =="
$PY -m unittest discover -s tests

echo
echo "== Prüfung der Seite =="
$PY tools/pruefen.py
