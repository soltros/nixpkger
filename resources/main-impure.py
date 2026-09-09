#!/usr/bin/env python3
"""Compatibility entry point for the former impure variant."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nixpkger_core.cli import main

if __name__ == '__main__':
    raise SystemExit(main(default_impure=True))
