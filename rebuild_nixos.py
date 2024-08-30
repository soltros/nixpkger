import subprocess
import logging
import sys

def rebuild_nixos():
    try:
        subprocess.run(["sudo", "nixos-rebuild", "switch"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to rebuild NixOS configuration: {e}")
        sys.exit(1)
