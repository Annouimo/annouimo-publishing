#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

writing_source="$(mktemp -d)"
trap 'rm -rf "$writing_source"' EXIT

git clone --quiet --depth 1 --branch main https://github.com/Annouimo/annouimo-writing.git "$writing_source"
printf 'Writing revision: %s\n' "$(git -C "$writing_source" rev-parse HEAD)"
python3 -m venv "$writing_source/.build-venv"
"$writing_source/.build-venv/bin/pip" --quiet install 'PyYAML>=6,<7'
"$writing_source/.build-venv/bin/python" scripts/import-writing.py "$writing_source"
export WHY_NOTES_PREVIEW=1
npm run prepare:content
./node_modules/.bin/astro build
