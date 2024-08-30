import subprocess
import logging
import sys

def search_packages(query):
    try:
        output = subprocess.check_output(["nix-env", "-qaP", query], stderr=subprocess.DEVNULL)
        lines = output.decode("utf-8").splitlines()
        for line in lines:
            print(line.replace("nixos.", ""))
    except subprocess.CalledProcessError as e:
        logging.error(f"Error: Unable to search for packages matching '{query}'. {e}")
        sys.exit(1)
