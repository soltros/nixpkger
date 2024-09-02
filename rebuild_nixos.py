import subprocess
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def rebuild_nixos():
    try:
        logging.info("Starting NixOS rebuild...")
        result = subprocess.run(
            ["sudo", "nixos-rebuild", "switch"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        logging.info(result.stdout)  # Logs the standard output
        if result.stderr:
            logging.error(result.stderr)  # Logs any error output
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to rebuild NixOS configuration: {e}")
        logging.error(e.stdout)  # Log any output from the command
        logging.error(e.stderr)  # Log any error output from the command
        sys.exit(1)

if __name__ == "__main__":
    rebuild_nixos()
