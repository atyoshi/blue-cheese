#!/usr/bin/env bash
set -euo pipefail

project_dir=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().parent)' "${BASH_SOURCE[0]}")
target_dir="$HOME/.local/bin"
target="$target_dir/bluecheese"

mkdir -p -- "$target_dir"
if [[ -e "$target" && ! -L "$target" ]]; then
    printf 'Refusing to replace existing file: %s\n' "$target" >&2
    exit 1
fi
if [[ -L "$target" && "$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$target")" != "$project_dir/bluecheese" ]]; then
    printf 'Refusing to replace existing link: %s\n' "$target" >&2
    exit 1
fi
ln -sfn -- "$project_dir/bluecheese" "$target"
printf 'Installed %s -> %s\n' "$target" "$project_dir/bluecheese"
if [[ ":$PATH:" != *":$target_dir:"* ]]; then
    printf 'Add %s to your PATH to use bluecheese from any directory.\n' "$target_dir"
fi
