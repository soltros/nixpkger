#!/bin/bash

# Install necessary packages
nix-env -iA nixos.python311Full nixos.wget nixos.unzip

# Download the main.zip file
wget https://github.com/soltros/nixpkger/archive/refs/heads/main.zip -O v3.zip

# Unzip the downloaded file
unzip v3.zip
mv nixpkger-main/ ~/scripts/
mkdir -p ~/scripts/python/
cd ~/scripts/
mv *.py python/
chmod +x nixpkger

# Add alias to .bashrc if it doesn't exist
grep -qxF "alias nixpkger='bash ~/scripts/nixpkger'" ~/.bashrc || echo "alias nixpkger='bash ~/scripts/nixpkger'" >> ~/.bashrc

# Download and copy the apps.nix file
wget https://raw.githubusercontent.com/soltros/configbuilder/main/modules/apps.nix
sudo cp apps.nix /etc/nixos/

echo "Setup completed successfully!"
