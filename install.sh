#!/bin/sh
set -eu

command -v python3 >/dev/null 2>&1 || { echo 'Python 3.9 or newer is required.' >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'

source_dir=${1:-}
temporary_dir=
trap '[ -z "$temporary_dir" ] || rm -rf "$temporary_dir"' EXIT
trap 'exit 1' HUP INT TERM
if [ -z "$source_dir" ]; then
    candidate=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
    if [ -d "$candidate/nixpkger_core" ]; then
        source_dir=$candidate
    else
        command -v git >/dev/null 2>&1 || { echo 'Git is required.' >&2; exit 1; }
        temporary_dir=$(mktemp -d)
        git clone --depth 1 https://github.com/soltros/nixpkger.git "$temporary_dir/repo"
        source_dir="$temporary_dir/repo"
    fi
fi
prefix=${NIXPKGER_PREFIX:-$HOME/.local}
mkdir -p "$prefix"
prefix=$(CDPATH= cd -- "$prefix" && pwd)
install_dir="$prefix/share/nixpkger"
bin_dir="$prefix/bin"
mkdir -p "$install_dir" "$bin_dir"
cp -R "$source_dir/nixpkger_core" "$install_dir/"
cp "$source_dir/main.py" "$source_dir/nixpkger" "$install_dir/"
python3 - "$install_dir" "$bin_dir/nixpkger" <<'PY'
from pathlib import Path
import sys
root, launcher = sys.argv[1:]
Path(launcher).write_text(
    '#!/usr/bin/env python3\nimport runpy\nimport sys\n'
    f'sys.path.insert(0, {root!r})\n'
    f'runpy.run_path({str(Path(root) / "nixpkger")!r}, run_name="__main__")\n',
    encoding='utf-8',
)
PY
chmod +x "$bin_dir/nixpkger"
printf 'Installed nixpkger. Add %s to PATH.\n' "$bin_dir"
