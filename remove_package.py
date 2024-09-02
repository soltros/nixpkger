#!/usr/bin/env python3

import re
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_config_file(file_path):
    try:
        with open(file_path, "r") as config_file:
            return config_file.read()
    except FileNotFoundError:
        logging.error(f"apps.nix file {file_path} not found.")
        sys.exit(1)

def write_config_file(file_path, content):
    try:
        with open(file_path, "w") as config_file:
            config_file.write(content)
    except IOError as e:
        logging.error(f"Failed to write to {file_path}: {e}")
        sys.exit(1)

def remove_package(packages, package_to_remove):
    if package_to_remove in packages:
        packages.remove(package_to_remove)
        return f"Removed package {package_to_remove} from the list."
    else:
        return f"Package {package_to_remove} is not in the list."

def rebuild_nixos():
    try:
        subprocess.run(["sudo", "nixos-rebuild", "switch"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to rebuild NixOS configuration: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: remove_package.py <package name>")
        sys.exit(1)

    config_file_path = "/etc/nixos/apps.nix"
    config_contents = read_config_file(config_file_path)

    package_list_match = re.search(r'environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[(.*?)\];', config_contents, re.DOTALL)
    if package_list_match:
        package_list = package_list_match.group(1).strip()
        packages = package_list.split()
    else:
        logging.error("Package list not found in the apps.nix configuration file.")
        sys.exit(1)

    package_to_remove = sys.argv[1]
    result = remove_package(packages, package_to_remove)
    print(result)

    if "Removed" in result:
        new_package_list = " ".join(packages)
        updated_config_contents = re.sub(r'(environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[).*?(];)',
                                         f'\\1\n    {new_package_list}\n  \\2', config_contents, flags=re.DOTALL)
        write_config_file(config_file_path, updated_config_contents)
        print("apps.nix file updated.")
        rebuild_nixos()
        print("NixOS rebuild completed.")

if __name__ == "__main__":
    main()
