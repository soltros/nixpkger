import logging
import os
import shutil

def restore_config(restore_path):
    if not restore_path.endswith('.nix'):
        logging.error("Error: Provided path does not have a '.nix' extension.")
        return

    dir_path, file_name = os.path.split(restore_path)
    base_name, _ = os.path.splitext(file_name)
    new_path = os.path.join(dir_path, 'apps.nix')
    os.rename(restore_path, new_path)
    backup_dir = "/etc/nixos/app_snapshots"
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"config_backup_{base_name}.nix")
    shutil.copy(new_path, backup_path)
    config_path = "/etc/nixos/apps.nix"
    shutil.move(new_path, config_path)
    logging.info("Configuration restored and backup created.")
