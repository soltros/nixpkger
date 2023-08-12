import re
import subprocess

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

# Function to rebuild the NixOS configuration
def rebuild_nixos():
    subprocess.run(["sudo", "nixos-rebuild", "switch"])

# Main function that orchestrates the configuration update process
def main():
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

    # Prompt the user to choose whether to install or uninstall a package
    action = input("Do you want to (i)nstall or (u)ninstall a package? ").strip().lower()

    if action == "i":
        # Prompt the user for the package to install
        new_package = input("Enter the package you want to install: ").strip()
        result = add_package(packages, new_package)
    elif action == "u":
        # Prompt the user for the package to uninstall
        package_to_remove = input("Enter the package you want to uninstall: ").strip()
        result = remove_package(packages, package_to_remove)
    else:
        print("Invalid action. Please choose 'i' for install or 'u' for uninstall.")
        exit(1)

    # Generate an updated package list as a string
    new_package_list = " ".join(packages)

    # Replace the old package list in the configuration contents with the updated one
    updated_config_contents = re.sub(r'(environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[).*?(];)', f'\\1\n    {new_package_list}\n  \\2', config_contents, flags=re.DOTALL)

    # Write the updated configuration contents back to the file
    write_config_file(config_file_path, updated_config_contents)

    print("Configuration file updated.")
    print(result)

    # Rebuild the NixOS configuration
    rebuild_nixos()
    print("NixOS rebuild completed.")

# Entry point of the script
if __name__ == "__main__":
    main()
