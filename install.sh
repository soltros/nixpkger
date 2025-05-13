#!/bin/bash

# Install necessary packages
nix-env -iA nixos.python311Full nixos.wget nixos.git

##Install
git clone https://github.com/soltros/nixpkger
cd nixpkger/
mkdir -p ~/scripts/
mkdir -p ~/scripts/python/
mv *.py ~/scripts/python/
mv resources/ ~/scripts/
mv nixpkger ~/scripts

echo "Be sure to replace main.py with the flake variant if you plan to use flakes with Nixpkger.
