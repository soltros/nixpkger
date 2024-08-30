import subprocess
import logging
import sys

def update_nixos():
    try:
        subprocess.run(["nix-env", "-u"], check=True)
        subprocess.run(["sudo", "nix-channel", "--update"], check=True)
        subprocess.run(["sudo", "nixos-rebuild", "switch", "--upgrade"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update NixOS configuration: {e}")
        sys.exit(1)
