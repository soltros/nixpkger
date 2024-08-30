#!/bin/bash

nix-env -iA nixos.python311Full

git clone https://github.com/soltros/nixpkger

cp ~/nixpkg.py/nixpkger ~/scripts/
cp ~/nixpkg.py/python/*.py ~/scripts/python/

echo -e "\nalias nixpkger='bash ~/scripts/nixpkger'" >> ~/.bashrc

wget https://raw.githubusercontent.com/soltros/configbuilder/main/modules/apps.nix

sudo cp apps.nix /etc/nixos/
