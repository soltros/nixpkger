#!/bin/bash
nix-channel --add https://nixos.org/channels/nixos-24.05 nixos

nix-channel --update

mkdir -p ~/scripts/
cd ~/scripts/

wget https://raw.githubusercontent.com/soltros/nixpkg.py/main/tools/nix-env-nixpkgs.py
chmod +x nix-env-nixpkgs.py

echo " " >>  ~/.bashrc
echo "## Nix" >>  ~/.bashrc
echo "export XDG_DATA_DIRS=~/.local/share/:~/.nix-profile/share:/usr/share" >>  ~/.bashrc
echo "export NIXPKGS_ALLOW_UNFREE=1" >> ~/.bashrc
echo "alias nixpkg='python ~/scripts/nix-env-nixpkgs.py'" >>  ~/.bashrc
echo "alias nix-update='nix-env -u "*"'" >>  ~/.bashrc
source ~/.bashrc
echo "use 'nixpkg appname' to install apps."
echo "use 'nixpkg-update' to update installed apps."
