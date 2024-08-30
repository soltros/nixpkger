import datetime
import os
from write_config_file import write_config_file

def create_snapshot(config_contents):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    snapshot_dir = "/etc/nixos/app_snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshot_path = os.path.join(snapshot_dir, f"app_snapshot_{timestamp}.nix")
    write_config_file(snapshot_path, config_contents)
    return snapshot_path
