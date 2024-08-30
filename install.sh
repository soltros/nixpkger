#!/bin/bash

# Check if the script is being run with bash
if [ "$(basename "$0")" != "bash" ]; then
  echo "Error: This script must be run with bash"
  exit 1
fi

# Install necessary packages
nix-env -iA nixos.python311Full nixos.wget nixos.unzip

# Download the main.zip file
curl -f -o /tmp/main.zip https://github.com/soltros/nixpkger/archive/refs/heads/main.zip || { echo "Failed to download main.zip"; exit 1; }

# Create the scripts directory
mkdir -p ~/scripts/
mkdir -p ~/scripts/python/

# Unzip the downloaded file
unzip /tmp/main.zip -d /tmp/ || { echo "Failed to unzip main.zip"; exit 1; }

# Move files from the unzipped directory to the final destination
mv "/tmp/nixpkger-main/*" ~/scripts/ || { echo "Failed to move files"; exit 1; }
mv "~/scripts/*.py" ~/scripts/python/

# Clean up temporary files
rm "/tmp/main.zip"
rm -rf "/tmp/nixpkger-main/"

# Add alias to .bashrc if it doesn't exist
grep -qxF "alias nixpkger='bash ~/scripts/nixpkger'" ~/.bashrc || echo "alias nixpkger='bash ~/scripts/nixpkger'" >> ~/.bashrc

# Download and copy the apps.nix file
if [ ! -f /etc/nixos/apps.nix ]; then
  curl -f -o /tmp/apps.nix https://raw.githubusercontent.com/soltros/configbuilder/main/modules/apps.nix || { echo "Failed to download apps.nix"; exit 1; }
  sudo cp /tmp/apps.nix /etc/nixos/ || { echo "Failed to copy apps.nix to /etc/nixos/"; exit 1; }
else
  echo "apps.nix already exists in /etc/nixos/, skipping download and copy"
fi

echo "Setup completed successfully!"
