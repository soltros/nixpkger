def print_help():
    help_text = """
Usage: nixpkg.py <action> [<package/query>]

Actions:
  install <package name(s)>                          : Install one or more packages to apps.nix
  install --category category-name <package name(s)> : Install one more more packages to category-name.nix
  add-category										 : Add a category nix file to your configuration.nix file imports area.
  remove <package name(s)>                           : Remove one or more packages
  remove --category category-name <package name(s)>  : Remove one or more packages from a specified category.nix file.
  search <query>                                     : Search for NixOS packages
  list                                               : List installed packages in apps.nix
  list-categories category-file.nix					 : List all installed packages in a specific category.nix file.
  update                                             : Update NixOS configuration and rebuild
  snapshot                                           : Create a snapshot of the apps.nix configuration
  restore <path>                                     : Restore the configuration from a snapshot or backup
  backup                                             : Create a backup of the current configuration

Options:
  --help                                             : Display this help message
"""
    print(help_text)
