#!/bin/bash

## Setup env
nix-env -iA nixos.python311Full nixos.wget

## Download files
cd ~/Downloads/
wget https://raw.githubusercontent.com/soltros/nixpkg.py/main/install.py
wget https://raw.githubusercontent.com/soltros/configbuilder/main/modules/apps.nix
python install.py

## Place apps.nix
sudo mv apps.nix /etc/nixos/

## Add alias to .bashrc
alias_line="alias nixpkg='sudo python ~/scripts/nixpkg.py'"

if [ -f "$HOME/.bashrc" ]; then
    if grep -qF "$alias_line" "$HOME/.bashrc"; then
        echo "Alias 'nixpkg' already exists in .bashrc."
    else
        echo "Adding alias 'nixpkg' to .bashrc..."
        echo "$alias_line" >> "$HOME/.bashrc"
        echo "Alias added successfully."
    fi
else
    echo "Creating a new .bashrc file..."
    echo "$alias_line" > "$HOME/.bashrc"
    echo "Alias 'nixpkg' added to .bashrc."
fi

echo "Setup complete."
