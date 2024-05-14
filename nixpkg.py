#!/usr/bin/env python3

import re
import subprocess
import sys
import shutil
import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to read the contents of a configuration file
def read_config_file(file_path):
    try:
        with open(file_path, "r") as config_file:
            return config_file.read()
    except FileNotFoundError:
        logging.error(f"Configuration file {file_path} not found.")
        sys.exit(1)

# Function to write content to a configuration file
def write_config_file(file_path, content):
    try:
        with open(file_path, "w") as config_file:
            config_file.write(content)
    except IOError as e:
        logging.error(f"Failed to write to {file_path}: {e}")
        sys.exit(1)

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
        search_command = ["nix-env", "-qa", query]
        result = subprocess.run(search_command, capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            logging.error(f"Search command failed with exit status {result.returncode}")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error: Unable to retrieve search results for '{query}'. {e}")
        sys.exit(1)

# Function to list installed packages
def list_packages(packages):
    if packages:
        return "Installed packages:\n" + "\n".join(packages)
    else:
        return "No packages are currently installed."

# Function to rebuild the NixOS configuration
def rebuild_nixos():
    try:
        subprocess.run(["sudo", "nixos-rebuild", "switch"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to rebuild NixOS configuration: {e}")
        sys.exit(1)

# Function to update the NixOS configuration with the latest changes
def update_nixos():
    try:
        subprocess.run(["nix-env", "-u"], check=True)
        subprocess.run(["sudo", "nix-channel", "--update"], check=True)
        subprocess.run(["sudo", "nixos-rebuild", "switch", "--upgrade"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update NixOS configuration: {e}")
        sys.exit(1)

def create_snapshot(config_contents):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    snapshot_dir = "/etc/nixos/configuration_snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshot_path = os.path.join(snapshot_dir, f"config_snapshot_{timestamp}.nix")
    write_config_file(snapshot_path, config_contents)
    return snapshot_path

def restore_config(restore_path):
    if not restore_path.endswith('.nix'):
        logging.error("Error: Provided path does not have a '.nix' extension.")
        return

    dir_path, file_name = os.path.split(restore_path)
    base_name, _ = os.path.splitext(file_name)
    new_path = os.path.join(dir_path, 'configuration.nix')
    os.rename(restore_path, new_path)
    backup_dir = "/etc/nixos/configuration_snapshots"
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"config_backup_{base_name}.nix")
    shutil.copy(new_path, backup_path)
    config_path = "/etc/nixos/configuration.nix"
    shutil.move(new_path, config_path)
    logging.info("Configuration restored and backup created.")

def create_backup(config_file_path):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = "/etc/nixos/configuration_backups"
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"config_backup_{timestamp}.nix")
    shutil.copy(config_file_path, backup_path)
    return backup_path

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
  backup                    : Create a backup of the current configuration

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

    config_file_path = "/etc/nixos/configuration.nix"
    config_contents = read_config_file(config_file_path)

    package_list_match = re.search(r'environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[(.*?)\];', config_contents, re.DOTALL)
    if package_list_match:
        package_list = package_list_match.group(1).strip()
        packages = package_list.split()
    else:
        logging.error("Package list not found in the configuration file.")
        exit(1)

    action = sys.argv[1]

    if action == "install":
        if len(sys.argv) < 3:
            print("Usage: nixpkg.py install <package name(s)>")
            exit(1)
        packages_to_install = sys.argv[2:]
        for package in packages_to_install:
            print(add_package(packages, package))
        print(f"Packages installed: {', '.join(packages_to_install)}")
    elif action == "remove":
        if len(sys.argv) < 3:
            print("Usage: nixpkg.py remove <package name(s)>")
            exit(1)
        packages_to_remove = sys.argv[2:]
        for package in packages_to_remove:
            print(remove_package(packages, package))
        print(f"Packages removed: {', '.join(packages_to_remove)}")
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
    elif action == "backup":
        backup_path = create_backup(config_file_path)
        print(f"Configuration backup created: {backup_path}")
    else:
        print("Invalid action. Please choose 'install', 'remove', 'search', 'update', 'list', 'snapshot', 'backup', or 'restore'.")
        exit(1)

    new_package_list = " ".join(packages)
    updated_config_contents = re.sub(r'(environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[).*?(];)', f'\\1\n    {new_package_list}\n  \\2', config_contents, flags=re.DOTALL)
    write_config_file(config_file_path, updated_config_contents)
    print("Configuration file updated.")

    rebuild_nixos()
    print("NixOS rebuild completed.")

# Entry point of the script
if __name__ == "__main__":
    main()
