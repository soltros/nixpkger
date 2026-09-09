"""Resolve explicit module paths and discover modules in configuration trees."""
import os
from pathlib import Path

from .config import ConfigError

IGNORED = {'.git', '.direnv', '.cache', '.venv', 'result', 'app_backups', 'app_snapshots', 'node_modules'}


def find_module(root, name, explicit=None):
    if explicit is not None:
        path = Path(explicit).expanduser()
        return (root / path).resolve()
    matches = set()
    def inaccessible(error):
        raise ConfigError(f'Cannot search configuration directory: {error}')

    for directory, children, files in os.walk(root, onerror=inaccessible):
        children[:] = sorted(child for child in children if child not in IGNORED)
        if name in files:
            matches.add((Path(directory) / name).resolve())
    if len(matches) > 1:
        choices = '\n  '.join(str(path) for path in sorted(matches))
        option = '--apps-file' if name == 'apps.nix' else '--module-file'
        raise ConfigError(f'Multiple {name} files found. Select one with {option}:\n  {choices}')
    return next(iter(matches), root / name)


def resolve_locations(args):
    explicit_root = args.config_dir
    root = Path(explicit_root or '/etc/nixos').expanduser().resolve()
    flake = None
    reference = None
    if args.flake is not None:
        path, separator, host = args.flake.partition('#')
        candidate = Path(path or '.').expanduser()
        # Explicit config-dir remains a useful base for relative flake references.
        base = root if explicit_root is not None else Path.cwd()
        flake = (base / candidate).resolve()
        if flake.name == 'flake.nix' and flake.is_file():
            flake = flake.parent
        if not (flake / 'flake.nix').is_file():
            raise ConfigError(f'Local flake not found: {flake / "flake.nix"}')
        reference = str(flake) + (separator + host if separator else '')
        if explicit_root is None:
            root = flake
    return root, flake, reference


def absolute_location_options(argv, args):
    """Expand user-relative locations before sudo changes the effective user."""
    root, _, reference = resolve_locations(args)
    values = {'--config-dir': str(root), '--flake': reference}
    for option, path in (('--apps-file', args.apps_file), ('--module-file', args.module_file)):
        if path is not None:
            values[option] = str((root / path.expanduser()).resolve())
    result = []
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == args.action:
            result.extend(argv[index:])
            break
        option, separator, _ = argument.partition('=')
        if option in values:
            result.extend([option, values[option]])
            index += 1 if separator else 2
        else:
            result.append(argument)
            index += 1
    return result
