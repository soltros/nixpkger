import re
from category import get_category_file, ensure_category_file_exists

def remove_package_from_category(category, packages):
    """Removes packages from the specified category file."""
    category_file_path = get_category_file(category)
    ensure_category_file_exists(category_file_path)

    with open(category_file_path, 'r') as f:
        config_contents = f.read()

    removed_packages = []
    for package in packages:
        if package in config_contents:
            print(f"Warning: Removing package '{package}' from category '{category}'. Are you sure? (y/n)")
            response = input()
            if response.lower() != 'y':
                print("Aborting removal.")
                return []
            config_contents = re.sub(r'\s*' + re.escape(package) + r'\n', '', config_contents)
            removed_packages.append(package)
            print(f"Removed {package} from {category_file_path}")
        else:
            print(f"{package} not found in {category_file_path}")

    with open(category_file_path, 'w') as f:
        f.write(config_contents)

    return removed_packages
