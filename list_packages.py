import os
import re
from read_config_file import read_config_file

def list_packages():
    config_file_path = "/etc/nixos/apps.nix"
    config_contents = read_config_file(config_file_path)
    package_list_match = re.search(r'environment\.systemPackages\s*=\s*with\s+pkgs;\s*\[(.*?)\];', config_contents, re.DOTALL)
    if package_list_match:
        package_list = package_list_match.group(1).strip()
        packages = package_list.split()
        print("Installed packages:")
        for package in packages:
            print(package)
    else:
        print("No packages are currently installed.")
