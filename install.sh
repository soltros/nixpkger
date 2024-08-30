#!/bin/bash

nix-env -iA nixos.python311Full nixos.wget nixos.unzip

wget https://github.com/soltros/nixpkger/archive/refs/heads/main.zip
mkdir -p ~/scripts/
mkdir -p ~/scripts/temp_unzip/
unzip main.zip -d ~/scripts/temp_unzip/
mv ~/scripts/temp_unzip/nixpkger-main/* ~/scripts/
rm main.zip
rm -rf ~/scripts/temp_unzip/

cp ~/nixpkg.py/nixpkger ~/scripts/
cp ~/nixpkg.py/python/*.py ~/scripts/python/

echo -e "\nalias nixpkger='bash ~/scripts/nixpkger'" >> ~/.bashrc

wget https://raw.githubusercontent.com/soltros/configbuilder/main/modules/apps.nix

sudo cp apps.nix /etc/nixos/
