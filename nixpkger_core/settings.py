"""Persistent, per-user JSON settings for Nixpkger."""
import json
import os
from pathlib import Path
import tempfile
import subprocess
import pwd

from .config import ConfigError

def settings_path():
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config').expanduser() / 'nixpkger' / 'config.json'

def read_settings(path=None):
    path = Path(path) if path is not None else settings_path()
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ConfigError(f'Cannot read {path}: {error}') from error
    if not isinstance(obj, dict) or ('flake' in obj and not isinstance(obj['flake'], str)):
        raise ConfigError(f'Invalid Nixpkger JSON configuration: {path}')
    if 'branch' in obj and not isinstance(obj['branch'], str):
        raise ConfigError('Configured Git branch must be a string.')
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


def git_branch(directory):
    try:
        result = subprocess.run(['git', '-C', str(directory), 'symbolic-ref', '--quiet', '--short', 'HEAD'],
                                check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise ConfigError(f'Cannot determine active Git branch in {directory}: {error}') from error
    branch = result.stdout.strip()
    if not branch:
        raise ConfigError(f'No active Git branch in {directory}.')
    return branch


def verify_branch(directory, expected):
    actual = git_branch(directory)
    if actual != expected:
        raise ConfigError(f'Git branch mismatch in {directory}: configured {expected!r}, currently {actual!r}. '
                          'Switch branches deliberately, then reconfigure Nixpkger if needed.')


def mutation_settings():
    """Read invoking user's JSON settings during direct sudo execution."""
    if os.geteuid() != 0 or not os.environ.get('SUDO_UID'):
        return read_settings()
    try:
        uid = int(os.environ['SUDO_UID'])
        home = Path(pwd.getpwuid(uid).pw_dir)
    except (ValueError, KeyError) as error:
        raise ConfigError(f'Cannot identify invoking sudo user: {error}') from error
    if uid == 0:
        return read_settings()
    return read_settings(home / '.config' / 'nixpkger' / 'config.json')
