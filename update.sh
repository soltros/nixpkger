#!/bin/bash

# Define the Git repository URL
repo_url="https://github.com/soltros/nixpkg.py.git"

# Define the target directory for the nixpkg.py script
target_dir="$HOME/scripts"

# Check if Git is installed
if ! command -v git &> /dev/null; then
    echo "Git is not installed. Please install Git and run the update again."
    exit 1
fi

# Create the target directory if it doesn't exist
mkdir -p "$target_dir"

# Pull the latest version from the Git repository
echo "Pulling the latest version from the Git repository..."
if git clone "$repo_url" "$target_dir/nixpkg_temp"; then
    # Copy the nixpkg.py script to the target directory
    cp "$target_dir/nixpkg_temp/nixpkg.py" "$target_dir/"
    
    # Clean up the temporary directory
    rm -rf "$target_dir/nixpkg_temp"
    
    echo "Update completed successfully."
else
    echo "Update failed."
fi
