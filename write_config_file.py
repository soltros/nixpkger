import logging
import sys

def write_config_file(file_path, content):
    try:
        with open(file_path, "w") as config_file:
            config_file.write(content)
    except IOError as e:
        logging.error(f"Failed to write to {file_path}: {e}")
        sys.exit(1)
