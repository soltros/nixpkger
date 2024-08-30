import os

def list_categories():
    """Lists all packages from .nix files in /etc/nix/categories/"""
    categories_dir = "/etc/nix/categories/"
    
    # Create the categories directory if it doesn't exist
    if not os.path.exists(categories_dir):
        os.makedirs(categories_dir)

    packages = []

    for file in os.listdir(categories_dir):
        if file.endswith(".nix"):
            with open(os.path.join(categories_dir, file), 'r') as f:
                content = f.read()
                # Extract package names from the .nix file
                package_names = [line.strip() for line in content.splitlines() if line.startswith("  ")]
                packages.extend(package_names)

    if packages:
        return "Packages from categories:\n" + "\n".join(packages)
    else:
        return "No packages found in categories."

# Example usage:
print(list_categories())
