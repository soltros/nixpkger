"""Persistent, per-user JSON settings for Nixpkger."""
import json
import os
from pathlib import Path
import tempfile

from .config import ConfigError

def settings_path():
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config').expanduser() / 'nixpkger' / 'config.json'

def read_settings():
    path = settings_path()
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ConfigError(f'Cannot read {path}: {error}') from error
    if not isinstance(obj, dict) or ('flake' in obj and not isinstance(obj['flake'], str)):
        raise ConfigError(f'Invalid Nixpkger JSON configuration: {path}')
    return obj

def normalize_flake(raw):
    name, separator, host = raw.partition('#')
    if not name:
        raise ConfigError('Specify a local flake path.')
    target = Path(name).expanduser().resolve()
    if target.name == 'flake.nix' and target.is_file():
        target = target.parent
    if not (target / 'flake.nix').is_file():
        raise ConfigError(f'Local flake not found: {target / "flake.nix"}')
    return str(target) + (separator + host if separator else '')

def write_settings(obj):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.config-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(obj, stream, indent=2, sort_keys=True)
            stream.write('\n')
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
