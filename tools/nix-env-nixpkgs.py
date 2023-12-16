#!/usr/bin/env python

import sys
import subprocess

def install_program(program_name):
    try:
        # Use subprocess to execute the nix-env command
        install_command = f'nix-env -iA nixos.{program_name}'
        
        # Use subprocess.Popen to capture and display the output in real-time
        process = subprocess.Popen(install_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        # Display the output as the command is running
        for line in process.stdout:
            print(line, end='')
        
        for line in process.stderr:
            print(line, end='')
        
        # Wait for the command to finish
        process.wait()
        
        # Check if the installation was successful
        if process.returncode == 0:
            print(f"Successfully installed {program_name}")
            
            # Execute the cp command to copy .desktop files
            cp_command = 'cp -f ~/.nix-profile/share/applications/*.desktop ~/.local/share/applications/'
            cp_result = subprocess.run(cp_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if cp_result.returncode == 0:
                print("Copied .desktop files successfully")
            else:
                print(f"Error copying .desktop files:\n{cp_result.stderr.decode()}")
        else:
            print(f"Error installing {program_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python install_program.py <program_name>")
        sys.exit(1)

    program_name = sys.argv[1]
    install_program(program_name)
