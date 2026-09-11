"""Command dispatch and NixOS operations. No third-party Python dependencies."""
import argparse
from contextlib import contextmanager
import fcntl
from functools import cached_property
import json
import os
from pathlib import Path
import subprocess
import sys

from .config import (ConfigError, TEMPLATE, atomic_write, backup, category_path,
                     edit_import, edit_packages, packages)
from .locations import absolute_location_options, find_module, resolve_locations
from .sources import enable_source, search_soltros, current_reference
from . import __version__

MUTATIONS = {'install', 'remove', 'add-category', 'update', 'snapshot', 'backup', 'restore', 'gc'}


def parser(default_flake=None, default_impure=False):
    result = argparse.ArgumentParser(description='Manage packages declared in NixOS modules.', allow_abbrev=False)
    result.add_argument('--version', action='version', version=f'nixpkger {__version__}')
    result.add_argument('--config-dir', type=Path, help='tree to search for NixOS modules (defaults to the flake directory or /etc/nixos)')
    result.add_argument('--apps-file', type=Path, help='explicit package module, absolute or relative to the configuration directory')
    result.add_argument('--module-file', type=Path, help='module whose imports receive categories (defaults to discovered configuration.nix)')
    result.add_argument('--flake', default=default_flake, metavar='PATH[#HOST]',
                        help='local flake directory or flake.nix, optionally followed by #HOST')
    result.add_argument('--impure', action='store_true', default=default_impure)
    actions = result.add_subparsers(dest='action', required=True)
    for action in ('install', 'remove'):
        sub = actions.add_parser(action)
        sub.add_argument('--category')
        sub.add_argument('packages', nargs='+')
    search = actions.add_parser('search')
    search.add_argument('--json', action='store_true', help='print structured package metadata as JSON')
    search.add_argument('query')
    actions.add_parser('list')
    actions.add_parser('list-categories').add_argument('category')
    actions.add_parser('add-category').add_argument('category')
    update = actions.add_parser('update')
    update.add_argument('--source', choices=['system', 'soltros'], default='system',
                        help='update the system or the selected module’s pinned soltros packages')
    update.add_argument('--category', help='category to update with --source soltros')
    for action in ('snapshot', 'backup', 'gc'):
        actions.add_parser(action)
    actions.add_parser('restore').add_argument('path', type=Path)
    return result


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def nix_environment():
    environment = dict(os.environ)
    environment['NIX_CONFIG'] = environment.get('NIX_CONFIG', '') + '\nextra-experimental-features = nix-command flakes\n'
    return environment


def validate(source):
    run(['nix-instantiate', '--parse', '-'], input=source, text=True,
        stdout=subprocess.DEVNULL)


@contextmanager
def locked(root):
    # Keep the inode so every cooperating invocation locks the same file.
    with (root / '.nixpkger.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


class Application:
    def __init__(self, args):
        self.args = args
        self.root, self.flake, self.flake_ref = resolve_locations(args)

    @cached_property
    def apps(self):
        return find_module(self.root, 'apps.nix', self.args.apps_file)

    @cached_property
    def module(self):
        return find_module(self.root, 'configuration.nix', self.args.module_file)

    def rebuild(self, upgrade=False):
        command = ['nixos-rebuild', 'switch']
        if self.flake is not None:
            command += ['--flake', self.flake_ref]
        else:
            command += ['-I', f'nixos-config={self.module}']
            if upgrade:
                command.append('--upgrade')
        if self.args.impure:
            command.append('--impure')
        run(command, env=nix_environment())

    def change(self, changes):
        """Validate all edits before writing; restore source files on failure."""
        changes = {path.resolve(): source for path, source in changes.items()}
        originals = {}
        for path, source in changes.items():
            old = path.read_text(encoding='utf-8') if path.exists() else None
            if old != source:
                validate(source)
                originals[path] = old
        if not originals:
            print('No changes needed.')
            return
        for path, old in originals.items():
            if old is not None:
                location = backup(path, self.root / 'app_backups', path.stem + '_backup')
                print(f'Backup created: {location}')
        written = []
        try:
            for path in originals:
                atomic_write(path, changes[path])
                written.append(path)
            self.rebuild()
        except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
            for path in reversed(written):
                if originals[path] is None:
                    path.unlink()
                else:
                    atomic_write(path, originals[path])
            print('Previous configuration files restored. A failed activation may have partially changed the running system; inspect the rebuild output.', file=sys.stderr)
            raise
        print('Configuration updated and rebuilt.')

    def execute(self):
        action = self.args.action
        if action == 'search':
            if self.args.json:
                query = self.args.query
                if query.startswith('soltros.'):
                    query = query[len('soltros.'):]
                    source = 'github:soltros/soltros_nixpkgs'
                else:
                    source = 'nixpkgs'
                result = json.loads(run([*NIX, 'search', '--json', source, '--', query or '^'], capture_output=True, text=True).stdout)
                packages = []
                for attribute, details in sorted(result.items()):
                    details = dict(details)
                    details['attr'] = attribute.split('.', 3)[-1] if attribute.startswith('legacyPackages.') else attribute
                    packages.append(details)
                print(json.dumps(packages))
            elif self.args.query.startswith('soltros.'):
                search_soltros(self.args.query[len('soltros.'):], run)
            else:
                run(['nix-env', '-qa', '--', self.args.query])
        elif action == 'gc':
            run(['nix-collect-garbage', '-d'])
        elif action in {'list', 'list-categories'}:
            path = self.apps if action == 'list' else category_path(self.module.parent, self.args.category)
            values = packages(path.read_text(encoding='utf-8'))
            print('\n'.join(values) if values else 'No packages declared.')
        elif action in {'install', 'remove'}:
            category = self.args.category
            path = category_path(self.module.parent, category) if category else self.apps
            source = path.read_text(encoding='utf-8') if path.exists() else TEMPLATE
            if not path.exists() and (not category or action == 'remove'):
                raise ConfigError(f'Configuration file not found: {path}')
            updated = edit_packages(source, self.args.packages, action == 'remove')
            if action == 'install' and any(name.startswith('soltros.') for name in self.args.packages):
                updated = enable_source(updated, run)
            self.change({path: updated})
            if category and action == 'install':
                print(f'Ensure this category is imported using: nixpkger add-category {category}')
        elif action == 'add-category':
            config = self.module
            path = category_path(config.parent, self.args.category)
            source = config.read_text(encoding='utf-8')
            changes = {config: edit_import(source, path.stem)}
            if not path.exists():
                changes[path] = TEMPLATE
            self.change(changes)
        elif action in {'snapshot', 'backup'}:
            directory = 'app_snapshots' if action == 'snapshot' else 'app_backups'
            print(backup(self.apps, self.root / directory, f'app_{action}'))
        elif action == 'restore':
            if self.args.path.suffix != '.nix':
                raise ConfigError('Restore requires a .nix file.')
            source = self.args.path.read_text(encoding='utf-8')
            packages(source)
            self.change({self.apps: source})
        elif action == 'update':
            if self.args.source == 'soltros':
                path = category_path(self.module.parent, self.args.category) if self.args.category else self.apps
                source = path.read_text(encoding='utf-8')
                if not current_reference(source):
                    raise ConfigError('This module has no managed soltros source. Install a soltros package first.')
                self.change({path: enable_source(source, run, refresh=True)})
                return
            if self.args.category:
                raise ConfigError('--category requires update --source soltros.')
            # Updating a flake does not need a particular host's package module.
            if self.flake is None and self.apps.exists():
                print(f'Backup created: {backup(self.apps, self.root / "app_backups")}')
            if self.flake is not None:
                lock = self.flake / 'flake.lock'
                old = lock.read_text(encoding='utf-8') if lock.exists() else None
                try:
                    run(['nix', 'flake', 'update'], cwd=self.flake, env=nix_environment())
                    self.rebuild()
                except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                    if old is None:
                        lock.unlink(missing_ok=True)
                    else:
                        atomic_write(lock, old)
                    raise
            else:
                self.rebuild(upgrade=True)


def main(argv=None, *, default_flake=None, default_impure=False):
    args = parser(default_flake, default_impure).parse_args(argv)
    try:
        app = Application(args)
        if args.action in MUTATIONS:
            with locked(app.root):
                app.execute()
        else:
            app.execute()
        return 0
    except (ConfigError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        print(f'nixpkger: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('nixpkger: interrupted', file=sys.stderr)
        return 130


def launch():
    """Escalate writes consistently; keep search/list/help unprivileged."""
    args = parser().parse_args()
    if args.action in MUTATIONS and os.geteuid() != 0:
        try:
            argv = absolute_location_options(sys.argv[1:], args)
            os.execvp('sudo', ['sudo', '--', sys.executable, str(Path(__file__).resolve().parent.parent / 'main.py'), *argv])
        except (ConfigError, OSError) as error:
            print(f'nixpkger: {error}', file=sys.stderr)
            return 1
    return main()
