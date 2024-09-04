import os

def get_category_file(category):
    """Returns the path to the category file."""
    category_dir = "/etc/nixos/categories/"
    if not os.path.exists(category_dir):
        os.makedirs(category_dir)
    category_file = os.path.join(category_dir, f"{category}.nix")
    return category_file

def ensure_category_file_exists(category_file):
    """Creates the category file if it does not exist."""
    if not os.path.exists(category_file):
        with open(category_file, 'w') as file:
            file.write('''{ config, pkgs, ... }:

{
  # Add packages to the system environment
  environment.systemPackages = with pkgs; [

  ];
}
''')
        print(f"Created new category file: {category_file}")
    else:
        print(f"Using existing category file: {category_file}")
