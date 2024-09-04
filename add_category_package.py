import re

from category import get_category_file, ensure_category_file_exists
from read_config_file import read_config_file
from write_config_file import write_config_file

def add_package_to_category(category, packages):
    """Adds packages to the specified category file."""
    category_file = get_category_file(category)
    ensure_category_file_exists(category_file)

    config_contents = read_config_file(category_file)
    for package in packages:
        if package not in config_contents:
            config_contents = re.sub(r'(\[\n\s*)', f'\\1  {package}\n', config_contents)
            print(f"Added {package} to {category_file}")
        else:
            print(f"{package} already exists in {category_file}")

    write_config_file(category_file, config_contents)
