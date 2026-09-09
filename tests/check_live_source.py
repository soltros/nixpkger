"""Opt-in network/evaluation check; never builds or activates a system."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nixpkger_core.cli import run
from nixpkger_core.config import TEMPLATE, edit_packages
from nixpkger_core.sources import NIX, enable_source, search_soltros

source = enable_source(edit_packages(TEMPLATE, ['soltros.termsmith']), run)
expression = ('let module = (' + source + ') { config = {}; '
              'pkgs.stdenv.hostPlatform.system = "x86_64-linux"; }; '
              'in map (p: { inherit (p) pname drvPath; }) module.environment.systemPackages')
result = run([*NIX, 'eval', '--json', '--expr', expression], capture_output=True, text=True)
values = json.loads(result.stdout)
assert values[0]['pname'] == 'termsmith', values
assert values[0]['drvPath'].endswith('.drv'), values
print('Real pinned soltros module evaluates:', values[0]['pname'])
search_soltros('termsmith', run)
