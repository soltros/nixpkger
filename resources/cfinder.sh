#!/bin/bash

for category_file in "$@"; do
    if [ ! -f "/etc/nixos/categories/$category_file" ]; then
        echo "Error: Category file '$category_file' not found"
        exit 1
    fi
    echo "Packages in '$category_file':"
    sed -n '/environment.systemPackages = with pkgs; \[/,/\];/p' "/etc/nixos/categories/$category_file" | sed 's/.*\[//;s/\].*//;s/,/\
/g'
done
