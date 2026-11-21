#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
revision="$(cat notes.lock)"
if [[ ! "$revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "notes.lock must contain a full commit SHA" >&2
  exit 1
fi
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
if [[ -n "${NOTES_SOURCE:-}" ]]; then
  source_dir="$(realpath "$NOTES_SOURCE")"
else
  curl --fail --silent --show-error --location --retry 2 \
    "https://codeload.github.com/Annouimo/why-notes/tar.gz/$revision" |
    tar -xz -C "$temp" --strip-components=1
  source_dir="$temp"
fi
test -d "$source_dir/src/content/notes"
test -d "$source_dir/src/components"
mkdir -p src/content src/lib
rm -rf src/content/notes src/components
cp -R "$source_dir/src/content/notes" src/content/notes
cp -R "$source_dir/src/components" src/components
for file in continuity-element.ts continuity.ts examples.ts; do
  cp "$source_dir/src/lib/$file" "src/lib/$file"
done
printf 'Imported why-notes %s\n' "$revision"
