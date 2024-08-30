def list_packages(packages):
    if packages:
        return "Installed apps.nix packages:\n" + "\n".join(packages)
    else:
        return "No packages are currently installed."
