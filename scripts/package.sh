#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

out="${1:-CloudFlare-ImgBed.alfredworkflow}"
rm -f "$out"

zip -X -r "$out" info.plist icon.png src README.md \
  -x "*.pyc" "*__pycache__*" ".DS_Store"

echo "Wrote $out"
unzip -l "$out"
