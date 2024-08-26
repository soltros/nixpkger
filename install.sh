#!/bin/bash

nix-env -iA nixos.python311Full

git clone https://github.com/soltros/nixpkg.py

mkdir -p ~/scripts/

cp ~/nixpkg.py/nixpkg.py ~/scripts/

echo -e "\nalias nixpkg='sudo python ~/scripts/nixpkg.py'" >> ~/.bashrc

wget https://raw.githubusercontent.com/soltros/configbuilder/main/modules/apps.nix

sudo cp apps.nix /etc/nixos/
