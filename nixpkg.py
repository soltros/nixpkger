import re
import subprocess
import sys

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

# Function to search for NixOS packages using nix search
def search_packages(query):
    try:
        # Run the nix search command and capture the output
        search_command = ["nix", "search", query]
        search_output = subprocess.check_output(search_command, text=True)

        # Process the output to extract package names
        package_names = []
        for line in search_output.split('\n'):
            if line.strip():
                package_names.append(line.strip().split(" ", 1)[0])  # Extract only the package names

        return package_names
    except subprocess.CalledProcessError as e:
        return [f"Error: Unable to retrieve search results for '{query}'.", f"Command returned non-zero exit status: {e.returncode}"]

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
    subprocess.run(["sudo", "nixos-rebuild", "switch", "--upgrade"])

def print_help():
    help_text = """
Usage: nixpkg.py <action> [<package/query>]

Actions:
  install <package name(s)> : Install one or more packages
  remove <package name(s)>  : Remove one or more packages
  search <query>            : Search for NixOS packages
  list                      : List installed packages
  update                    : Update NixOS configuration and rebuild

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
        search_results = search_packages(search_query)
        print("Search results:")
        for package in search_results:
            print(package)
        exit(0)
    elif action == "list":
        print(list_packages(packages))
        exit(0)
    elif action == "update":
        update_nixos()
        print("NixOS update completed.")
    else:
        print("Invalid action. Please choose 'install', 'remove', 'search', 'update', or 'list'.")
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
