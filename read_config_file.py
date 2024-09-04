import logging
import sys

def read_config_file(file_path):
    try:
        with open(file_path, "r") as config_file:
            return config_file.read()
    except FileNotFoundError:
        logging.error(f"apps.nix file {file_path} not found.")
        sys.exit(1)
