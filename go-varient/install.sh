#!/bin/bash

mkdir -p ~/.binaries/
cd ~/.binaries/
wget https://github.com/soltros/nixpkg.py/raw/main/go-varient/nixpkg
chmod +x nixpkg
echo 'alias nixpkg="sudo ~/.binaries/./nixpkg"' >> ~/.bashrc
source ~/.bashrc
