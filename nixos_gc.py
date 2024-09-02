import subprocess
import logging

def nixos_gc():
    """Perform NixOS garbage collection."""
    try:
        # Execute the nix-collect-garbage command
        result = subprocess.run(["sudo", "nix-collect-garbage", "-d"], capture_output=True, text=True, check=True)
        print("NixOS garbage collection completed.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during NixOS garbage collection: {e.stderr}")
        print("NixOS garbage collection failed.")
