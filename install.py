import subprocess
import os
import urllib.request
import re
import logging
import sys
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to read the contents of a configuration file
def read_config_file(file_path):
    try:
        with open(file_path, "r") as config_file:
            return config_file.read()
    except FileNotFoundError:
        logging.error(f"File {file_path} not found.")
        sys.exit(1)

# Function to write content to a configuration file
def write_config_file(file_path, content):
    try:
        with open(file_path, "w") as config_file:
            config_file.write(content)
    except IOError as e:
        logging.error(f"Failed to write to {file_path}: {e}")
        sys.exit(1)

# Install Python 3.11 using nix-env
subprocess.run(["nix-env", "-iA", "nixos.python311Full"])

# Download the nixpkg.py script and save it to ~/scripts/nixpkg.py
url = "https://raw.githubusercontent.com/soltros/nixpkg.py/main/nixpkg.py"
response = urllib.request.urlopen(url)
with open(os.path.expanduser("~/scripts/nixpkg.py"), "w") as f:
    f.write(response.read().decode())
os.chmod(os.path.expanduser("~/scripts/nixpkg.py"), 0o755)

# Read the configuration.nix file
tmp_file = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
subprocess.run(["sudo", "cp", "/etc/nixos/configuration.nix", tmp_file.name])
tmp_file.close()
config_contents = read_config_file(tmp_file.name)

# Add ./apps.nix to the imports list
imports_match = re.search(r'imports\s*=\s*\[(.*?)\];', config_contents, re.DOTALL)
if imports_match:
    imports_list = imports_match.group(1).strip()
    imports = imports_list.split()
    if "./apps.nix" not in imports:
        imports.append("./apps.nix")
        new_imports_list = "\n    ".join(imports)
        updated_config_contents = re.sub(r'(imports\s*=\s*\[).*?(];)', f'\\1\n    {new_imports_list}\n  \\2', config_contents, flags=re.DOTALL)
        write_config_file(tmp_file.name, updated_config_contents)
        subprocess.run(["sudo", "mv", tmp_file.name, "/etc/nixos/configuration.nix"])
        logging.info("Added ./apps.nix to the imports list.")
    else:
        logging.info("./apps.nix is already in the imports list.")
else:
    logging.error("Imports list not found in the configuration.nix file.")
    sys.exit(1)
