The Nix Package Management Script (nixpkg.py) is a Python script designed to assist with managing NixOS packages and updating the NixOS configuration. This script provides a set of functions that allow you to perform various package-related tasks, such as installing, removing, searching for packages, listing installed packages, updating the NixOS configuration, and rebuilding the system configuration.


**Important Change: As of the latest version, all package management is now handled in a separate file called apps.nix, rather than the main configuration.nix file. This change allows for more flexibility and organization in managing your NixOS packages.**

To install:
```
curl https://raw.githubusercontent.com/soltros/nixpkg.py/main/setup.sh | bash
```

## Features

To install one or more packages, run the following command:

    nixpkg install <package name(s)>

Replace <package name(s)> with the names of the packages you wish to install. The script will add the specified packages to the list of packages in apps.nix and update the system configuration accordingly.

To remove one or more packages, use the following command:

    nixpkg remove <package name(s)>

Replace <package name(s)> with the names of the packages you want to remove. The script will remove the specified packages from the list of packages in apps.nix and update the system configuration.

To search for NixOS packages using a specific query, use the following command:

    nixpkg search <query>

To list all installed packages, run the following command:

    nixpkg list

 To update the NixOS configuration with the latest changes, use the following command:

    nixpkg update

This command will trigger an update of the NixOS configuration using the nixos-rebuild switch --upgrade command.

The script also provides the ability to create snapshots of the apps.nix configuration, and restore configurations from the snapshot. Use the following commands:

    nixpkg snapshot

Print Help

To view the "help" area of the script, use the --help flag:

    nixpkg --help

Important Notes: The script may require administrative privileges (sudo) for certain actions, such as updating the NixOS configuration. Be cautious when adding or removing packages, as it may affect the stability and functionality of your NixOS system.

##Contributing

If you would like to contribute to the development of this script, feel free to fork the repository and submit pull requests.
