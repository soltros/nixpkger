#!/bin/bash

# Define the alias to add to .bashrc
alias_line="alias nixpkg='sudo python ~/scripts/nixpkg.py'"

# Check if .bashrc exists
if [ -f "$HOME/.bashrc" ]; then
    # Check if the alias already exists in .bashrc
    if grep -qF "$alias_line" "$HOME/.bashrc"; then
        echo "Alias 'nixpkg' already exists in .bashrc."
    else
        echo "Adding alias 'nixpkg' to .bashrc..."
        echo "$alias_line" >> "$HOME/.bashrc"
        echo "Alias added successfully."
    fi
else
    # Create a new .bashrc file with the alias
    echo "Creating a new .bashrc file..."
    echo "$alias_line" > "$HOME/.bashrc"
    echo "Alias 'nixpkg' added to .bashrc."
fi

echo "Setup complete."
