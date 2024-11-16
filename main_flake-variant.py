#!/usr/bin/env python3

import re
import subprocess
import sys
import shutil
import datetime
import os
import logging
import tempfile

# Modules
from add_category_package import add_package_to_category
from remove_category_package import remove_package_from_category
from category_imports import add_category_import
from nixos_gc import nixos_gc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to read the contents of a configuration file
def read_config_file(file_path):
    try:
        with open(file_path, "r") as config_file:
            return config_file.read()
    except FileNotFoundError:
        logging.error(f"apps.nix file {file_path} not found.")
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
            if result.stdout.strip():
                print(result.stdout)
            else:
                print(f"No packages found for query: {query}")
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
        subprocess.run(["cd", "/etc/nixos/"], check=True)
        subprocess.run(["sudo", "nixos-rebuild", "switch", "--flake", ".#"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to rebuild NixOS configuration: {e}")
        sys.exit(1)

# Function to run the category-finder script.
def execute_bash_script(script_path, file_name):
    try:
        # Execute the bash command and capture the output
        result = subprocess.run(["bash", script_path, file_name], capture_output=True, text=True, check=True)
        # Return the output
        return result.stdout
    except subprocess.CalledProcessError as e:
        # If the command fails, return the error
        return f"An error occurred: {e.stderr}"

def list_categories():
    if len(sys.argv) < 3:
        print("Usage: main.py list-categories <category-file>")
        return
    
    file_name = sys.argv[2]

    # Construct the full path to the script
    script_path = os.path.expanduser("~/scripts/resources/cfinder.sh")

    if not os.path.exists(script_path):
        print(f"Script not found: {script_path}")
        return

    # Execute the bash script with the given arguments
    output = execute_bash_script(script_path, file_name)

    # Display the output to the user
    print(output)

# Function to update the NixOS configuration with the latest changes
def update_nixos():
    try:
        subprocess.run(["nix-env", "-u"], check=True)
        subprocess.run(["cd", "/etc/nixos/"], check=True)
        subprocess.run(["sudo", "nix", "flake", "update"], check=True)
        subprocess.run(["sudo", "nixos-rebuild", "switch", "--flake", ".#"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update NixOS configuration: {e}")
        sys.exit(1)

def create_snapshot(config_contents):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    snapshot_dir = "/etc/nixos/app_snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshot_path = os.path.join(snapshot_dir, f"app_snapshot_{timestamp}.nix")
    write_config_file(snapshot_path, config_contents)
    return snapshot_path

def restore_config(restore_path):
    if not restore_path.endswith('.nix'):
        logging.error("Error: Provided path does not have a '.nix' extension.")
        return

    dir_path, file_name = os.path.split(restore_path)
    base_name, _ = os.path.splitext(file_name)
    new_path = os.path.join(dir_path, 'apps.nix')
    os.rename(restore_path, new_path)
    backup_dir = "/etc/nixos/app_snapshots"
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"config_backup_{base_name}.nix")
    shutil.copy(new_path, backup_path)
    config_path = "/etc/nixos/apps.nix"
    shutil.move(new_path, config_path)
    logging.info("Configuration restored and backup created.")

def create_backup(config_file_path):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = "/etc/nixos/app_backups"
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"app_backup_{timestamp}.nix")
    shutil.copy(config_file_path, backup_path)
    return backup_path

def print_help():
    help_text = """
Usage: nixpkger <action> [<package/query>]

Actions:
  install <package name(s)>                          : Install one or more packages to apps.nix
  install --category category-name <package name(s)> : Install one more more packages to category-name.nix
  add-category                                       : Add a category nix file to your configuration.nix file imports area.
  remove <package name(s)>                           : Remove one or more packages
  remove --category category-name <package name(s)>  : Remove one or more packages from a specified category.nix file.
  search <query>                                     : Search for NixOS packages
  list                                              : List installed packages in apps.nix
  list-categories category-file.nix                 : List all installed packages in a specific category.nix file.
  update                                            : Update NixOS configuration and rebuild
  snapshot                                          : Create a snapshot of the apps.nix configuration
  restore <path>                                    : Restore the configuration from a snapshot or backup
  backup                                            : Create a backup of the current configuration

Options:
  --help                                            : Display this help message
"""
    print(help_text)

def main():
    if "--help" in sys.argv:
        print_help()
        exit(0)

    if len(sys.argv) < 2:
        print("Usage: nixpkger <action> [<package/query>]")
        exit(1)

    action = sys.argv[1]
    
    # Handle category-based actions
    if "--category" in sys.argv:
        category_index = sys.argv.index("--category")
        category_name = sys.argv[category_index + 1]
        packages = sys.argv[category_index + 2:]

        if action == "install":
            add_package_to_category(category_name, packages)
            print(f"Packages installed in category '{category_name}': {', '.join(packages)}")
            rebuild_nixos()
        elif action == "remove":
            removed_packages = remove_package_from_category(category_name, packages)
            if removed_packages:
                print(f"Packages removed from category '{category_name}': {', '.join(removed_packages)}")
                rebuild_nixos()
            else:
                print(f"No packages removed from category '{category_name}'")
        else:
            print(f"Unknown action with category: {action}")
            print_help()
            exit(1)

    # Handle non-category-based actions
    else:
        config_file_path = "/etc/nixos/apps.nix"
        config_contents = read_config_file(config_file_path)

        package_list_match = re.search(r'environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[(.*?)\];', config_contents, re.DOTALL)
        if package_list_match:
            package_list = package_list_match.group(1).split()
        else:
            package_list = []

        if action == "install":
            packages_to_install = sys.argv[2:]
            for package in packages_to_install:
                print(add_package(package_list, package))
            updated_config_contents = re.sub(r'(environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[).*?(\];)', r'\1\n  ' + '\n  '.join(package_list) + r'\n\2', config_contents, flags=re.DOTALL)
            write_config_file(config_file_path, updated_config_contents)
            rebuild_nixos()

        elif action == "remove":
            packages_to_remove = sys.argv[2:]
            for package in packages_to_remove:
                print(remove_package(package_list, package))
            updated_config_contents = re.sub(r'(environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[).*?(\];)', r'\1\n  ' + '\n  '.join(package_list) + r'\n\2', config_contents, flags=re.DOTALL)
            write_config_file(config_file_path, updated_config_contents)
            rebuild_nixos()

        elif action == "search":
            if len(sys.argv) < 3:
                print("Usage: nixpkger search <query>")
                exit(1)
            query = sys.argv[2]
            search_packages(query)
        
        elif action == "list-categories":
            list_categories()

        elif action == "gc":
            nixos_gc()

        elif action == "add-category":
            if len(sys.argv) != 3:
                print("Usage: nixpkger add-category <category-name>")
                exit(1)
            category_name = sys.argv[2]
            add_category_import(category_name)
            rebuild_nixos()

        elif action == "list":
            print(list_packages(package_list))

        elif action == "update":
            create_backup(config_file_path)
            update_nixos()

        elif action == "snapshot":
            snapshot_path = create_snapshot(config_contents)
            print(f"Snapshot created at: {snapshot_path}")

        elif action == "restore":
            if len(sys.argv) < 3:
                print("Usage: nixpkger restore <snapshot_file>")
                exit(1)
            restore_path = sys.argv[2]
            restore_config(restore_path)
            rebuild_nixos()

        elif action == "backup":
            backup_path = create_backup(config_file_path)
            print(f"Backup created at: {backup_path}")

        else:
            print(f"Unknown action: {action}")
            print_help()
            exit(1)

if __name__ == "__main__":
    main()
