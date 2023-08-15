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

# Clone the repository into a temporary directory
echo "Cloning the repository..."
if git clone "$repo_url" "$target_dir/nixpkg_temp"; then
    # Move the contents of the cloned directory into the target directory
    mv "$target_dir/nixpkg_temp"/* "$target_dir/"
    
    # Clean up the temporary directory
    rm -rf "$target_dir/nixpkg_temp"
    
    echo "Update completed successfully."
else
    echo "Update failed."
fi
