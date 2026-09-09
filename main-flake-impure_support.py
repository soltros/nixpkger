#!/usr/bin/env python3
"""Compatibility entry point; prefer nixpkger --flake .# --impure."""
from nixpkger_core.cli import main

if __name__ == '__main__':
    raise SystemExit(main(default_flake='.#', default_impure=True))
