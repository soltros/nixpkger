#!/usr/bin/env python3

import re
import subprocess
import sys
import shutil
import datetime
import os

# Function to read the contents of a configuration file
def read_config_file(file_path):
    with open(file_path, "r") as config_file:
        return config_file.read()

# Function to write content to a configuration file
def write_config_file(file_path, content):
    with open(file_path, "w") as config_file:
        config_file.write(content)

# Function to add a package to a list of packages
def add_package(packages, new_package):
    if new_package not in packages:
        packages.append(new_package)
        return f"Added package {new_package} to the list."
    else:
        return f"Package {new_package} is already in the list."

# Function to remove a package from a list of packages
def remove_package(packages, package_to_remove):
    if package_to_remove in packages:
        packages.remove(package_to_remove)
        return f"Removed package {package_to_remove} from the list."
    else:
        return f"Package {package_to_remove} is not in the list."

# Function to search for NixOS packages using nix-env -qa
def search_packages(query):
    try:
        # Run the nix-env -qa command
        search_command = ["nix-env", "-qa", query]
        subprocess.run(search_command)
    except subprocess.CalledProcessError as e:
        print(f"Error: Unable to retrieve search results for '{query}'.")
        print(f"Command returned non-zero exit status: {e.returncode}")

# Function to list installed packages
def list_packages(packages):
    if packages:
        return "Installed packages:\n" + "\n".join(packages)
    else:
        return "No packages are currently installed."

# Function to rebuild the NixOS configuration
def rebuild_nixos():
    subprocess.run(["sudo", "nixos-rebuild", "switch"])

# Function to update the NixOS configuration with the latest changes
def update_nixos():
    subprocess.run(["nix-env", "-u"])
    subprocess.run(["sudo", "nix-channel", "--update"])
    subprocess.run(["sudo", "nixos-rebuild", "switch", "--upgrade"])

def create_snapshot(config_contents):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    snapshot_dir = "/etc/nixos/configuration_snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshot_path = os.path.join(snapshot_dir, f"config_snapshot_{timestamp}.nix")
    write_config_file(snapshot_path, config_contents)
    return snapshot_path

def restore_config(restore_path):
    # Check if the provided path ends with '.nix' extension
    if not restore_path.endswith('.nix'):
        print("Error: Provided path does not have a '.nix' extension.")
        return

    # Get the directory path and file name without the extension
    dir_path, file_name = os.path.split(restore_path)
    base_name, _ = os.path.splitext(file_name)

    # Rename the file to 'configuration.nix'
    new_path = os.path.join(dir_path, 'configuration.nix')
    os.rename(restore_path, new_path)

    # Create a copy of the restored configuration
    backup_dir = "/etc/nixos/configuration_snapshots"
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"config_backup_{base_name}.nix")
    shutil.copy(new_path, backup_path)

    # Move the configuration file to /etc/nixos
    config_path = "/etc/nixos/configuration.nix"
    shutil.move(new_path, config_path)

    print("Configuration restored and backup created.")


def print_help():
    help_text = """
Usage: nixpkg.py <action> [<package/query>]

Actions:
  install <package name(s)> : Install one or more packages
  remove <package name(s)>  : Remove one or more packages
  search <query>            : Search for NixOS packages
  list                      : List installed packages
  update                    : Update NixOS configuration and rebuild
  snapshot                  : Create a snapshot of the configuration
  restore <path>            : Restore the configuration from a snapshot or backup

Options:
  --help                    : Display this help message
"""
    print(help_text)

def main():
    if "--help" in sys.argv:
        print_help()
        exit(0)

    if len(sys.argv) < 2:
        print("Usage: nixpkg.py <action> [<package/query>]")
        exit(1)

    # Path to the NixOS configuration file
    config_file_path = "/etc/nixos/configuration.nix"

    # Read the contents of the configuration file
    config_contents = read_config_file(config_file_path)

    # Search for the package list within the configuration file
    package_list_match = re.search(r'environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[(.*?)\];', config_contents, re.DOTALL)
    if package_list_match:
        # Extract the package list and split it into individual package names
        package_list = package_list_match.group(1).strip()
        packages = package_list.split()
    else:
        print("Package list not found in the configuration file.")
        exit(1)

    action = sys.argv[1]

    if action == "install":
        if len(sys.argv) < 3:
            print("Usage: nixpkg.py install <package name(s)>")
            exit(1)
        packages_to_install = sys.argv[2:]
        for package in packages_to_install:
            result = add_package(packages, package)
        result = "Packages installed: " + ", ".join(packages_to_install)
    elif action == "remove":
        if len(sys.argv) < 3:
            print("Usage: nixpkg.py remove <package name(s)>")
            exit(1)
        packages_to_remove = sys.argv[2:]
        for package in packages_to_remove:
            result = remove_package(packages, package)
        result = "Packages removed: " + ", ".join(packages_to_remove)
    elif action == "search":
        if len(sys.argv) != 3:
            print("Usage: nixpkg.py search <query>")
            exit(1)
        search_query = sys.argv[2]
        search_packages(search_query)
        exit(0)
    elif action == "list":
        print(list_packages(packages))
        exit(0)
    elif action == "update":
        update_nixos()
        print("NixOS update completed.")
    elif action == "snapshot":
        snapshot_path = create_snapshot(config_contents)
        print(f"Configuration snapshot created: {snapshot_path}")
    elif action == "restore":
        if len(sys.argv) != 3:
            print("Usage: nixpkg.py restore <path>")
            exit(1)
        restore_path = sys.argv[2]
        restore_config(restore_path)
        print("Configuration restored.")
    else:
        print("Invalid action. Please choose 'install', 'remove', 'search', 'update', 'list', 'snapshot', 'backup', or 'restore'.")
        exit(1)

    # Generate an updated package list as a string
    new_package_list = " ".join(packages)

    # Replace the old package list in the configuration contents with the updated one
    updated_config_contents = re.sub(r'(environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[).*?(];)', f'\\1\n    {new_package_list}\n  \\2', config_contents, flags=re.DOTALL)

    # Write the updated configuration contents back to the file
    write_config_file(config_file_path, updated_config_contents)

    print("Configuration file updated.")

    # Rebuild the NixOS configuration
    rebuild_nixos()
    print("NixOS rebuild completed.")

# Entry point of the script
if __name__ == "__main__":
    main()
