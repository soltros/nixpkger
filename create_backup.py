import datetime
import os
import shutil

def create_backup(config_file_path):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = "/etc/nixos/app_backups"
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"app_backup_{timestamp}.nix")
    shutil.copy(config_file_path, backup_path)
    return backup_path
