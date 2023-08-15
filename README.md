Nix Package Management Script (nixpkg.py)

Nix Package Management Script (nixpkg.py)
=========================================

The Nix Package Management Script (`nixpkg.py`) is a Python script designed to assist with managing NixOS packages and updating the NixOS configuration. This script provides a set of functions that allow you to perform various package-related tasks, such as installing, removing, searching for packages, listing installed packages, updating the NixOS configuration, and rebuilding the system configuration.

Features
--------

1.  **Install Packages**  
    To install one or more packages, run the following command:
    
        python nixpkg.py install <package name(s)>
    
    Replace `<package name(s)>` with the names of the packages you wish to install. The script will add the specified packages to the list of system packages in the NixOS configuration and update the system configuration accordingly.
2.  **Remove Packages**  
    To remove one or more packages, use the following command:
    
        python nixpkg.py remove <package name(s)>
    
    Replace `<package name(s)>` with the names of the packages you want to remove. The script will remove the specified packages from the list of system packages in the NixOS configuration and update the system configuration.
3.  **Search for Packages**  
    To search for NixOS packages using a specific query, use the following command:
    
        python nixpkg.py search <query>
    
    Replace `<query>` with the search query you want to use. The script will display a list of package names that match the query using the `nix search` command.
4.  **List Installed Packages**  
    To list all installed packages, run the following command:
    
        python nixpkg.py list
    
    This command will display a list of currently installed packages on your NixOS system.
5.  **Update NixOS Configuration**  
    To update the NixOS configuration with the latest changes, use the following command:
    
        python nixpkg.py update
    
    This command will trigger an update of the NixOS configuration using the `nixos-rebuild switch --upgrade` command.
6.  **Create a Snapshot, and Restore**  
    The script also provides the ability to create snapshots of the configuration, and restore configurations from the snapshot. Use the following commands:
    
        python nixpkg.py snapshot
    
8.  **Print Help**  
    To view the "help" area of the script, use the `--help` flag:
    
        python nixpkg.py --help
    

Prerequisites
-------------

Before using the `nixpkg.py` script, make sure you have the following prerequisites:

1.  Python: The script requires Python to be installed on your system.

Usage
-----

1.  Clone the repository to your local machine:
    
        git clone https://github.com/soltros/nixpkg.py.git
    
2.  Add `python311Full` to `/etc/nixos/configuration.nix` under `environment.systemPackages`.


3. Run `install.sh` to install the script and setup the Bash alias. Once the nixpkg.py alias is set up in your `.bashrc`. you can use the script with `nixpkg <action>`.


Important Notes
---------------

*   The script may require administrative privileges (`sudo`) for certain actions, such as updating the NixOS configuration.
*   Be cautious when adding or removing packages, as it may affect the stability and functionality of your NixOS system.

Contributing
------------

If you would like to contribute to the development of this script, feel free to fork the repository and submit pull requests.

License
-------

This script is provided under the [GPLv3 License](LICENSE).

* * *
