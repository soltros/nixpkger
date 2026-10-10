"""Command dispatch and NixOS operations. No third-party Python dependencies."""
import argparse
from contextlib import contextmanager
import fcntl
from functools import cached_property
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from urllib.parse import quote

from .config import (ConfigError, TEMPLATE, atomic_write, backup, category_path,
                     edit_import, edit_packages, packages)
from .locations import absolute_location_options, find_module, resolve_locations
from .settings import read_settings, write_settings, normalize_flake
from .sources import (NIX, enable_source, search_nixos, search_soltros, search_options,
                       current_reference)
from .update import self_update
from . import __version__

MUTATIONS = {'install', 'remove', 'add-category', 'update', 'snapshot', 'backup', 'restore', 'gc'}


def parser(default_flake=None, default_impure=False):
    result = argparse.ArgumentParser(description='Manage packages declared in NixOS modules.', allow_abbrev=False)
    result.add_argument('--version', action='version', version=f'nixpkger {__version__}')
    result.add_argument('--migrate-to-package', action='store_true',
                        help='remove the legacy ~/.local/bin/nixpkger launcher (keeps JSON settings)')
    result.epilog = ('Flake setup wizard: nixpkger config --wizard\\n'
                     'Noninteractive setup: nixpkger config --set-flake ~/nixos-config#HOST\\n'
                     'Package migration: nixpkger --migrate-to-package')
    result.formatter_class = argparse.RawDescriptionHelpFormatter
    result.add_argument('--config-dir', type=Path, help='tree to search for NixOS modules (defaults to the flake directory or /etc/nixos)')
    result.add_argument('--apps-file', type=Path, help='explicit package module, absolute or relative to the configuration directory')
    result.add_argument('--module-file', type=Path, help='module whose imports receive categories (defaults to discovered configuration.nix)')
    result.add_argument('--flake', default=default_flake, metavar='PATH[#HOST]',
                        help='local flake directory or flake.nix, optionally followed by #HOST')
    result.add_argument('--impure', action='store_true', default=default_impure)
    result.add_argument('--allow-unfree', action='store_true', help='allow unfree packages during Nix evaluation')
    actions = result.add_subparsers(dest='action')
    for action in ('install', 'remove'):
        sub = actions.add_parser(action)
        sub.add_argument('--category')
        sub.add_argument('packages', nargs='+')
    search = actions.add_parser('search')
    search.add_argument('--json', action='store_true', help='print structured package metadata as JSON')
    selection = search.add_mutually_exclusive_group()
    selection.add_argument('--info', action='store_true', help='show detailed package metadata and usage')
    selection.add_argument('--options', action='store_true', help='search NixOS module options instead of packages')
    search.add_argument('--limit', type=int, default=50, help='maximum human-readable results (default: 50)')
    search.add_argument('query')
    actions.add_parser('list')
    actions.add_parser('self-update', help='check for and install the latest nixpkger release')
    configuration = actions.add_parser('config', help='show, configure, or launch the flake setup wizard (config --wizard)')
    configuration.add_argument('--wizard', action='store_true', help='interactive flake path and host setup')
    configuration.add_argument('--set-flake', metavar='PATH[#HOST]', help='save the default local flake')
    configuration.add_argument('--unset-flake', action='store_true', help='remove the saved default flake')
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


def nix_environment(allow_unfree=False):
    environment = dict(os.environ)
    environment['NIX_CONFIG'] = environment.get('NIX_CONFIG', '') + '\nextra-experimental-features = nix-command flakes\n'
    if allow_unfree:
        environment['NIXPKGS_ALLOW_UNFREE'] = '1'
    return environment


def validate(source):
    run(['nix-instantiate', '--parse', '-'], input=source, text=True,
        stdout=subprocess.DEVNULL)


def print_search_results(records, query, limit=50):
    total = len(records)
    records = records[:max(0, limit)]
    use_color = sys.stdout.isatty()
    blue = '\033[1;34m' if use_color else ''
    bold = '\033[1m' if use_color else ''
    reset = '\033[0m' if use_color else ''
    count = f'{len(records)} results' if len(records) == total else f'showing {len(records)} of {total} results'
    print(f'{bold}Nixpkgs search{reset}  {query!r}  ·  {count}')
    if not records:
        print('No nixpkgs packages matched.')
        return
    width = shutil.get_terminal_size((100, 24)).columns
    attr_width = min(48, max(len(str(item.get('attr', ''))) for item in records))
    attr_width = max(12, attr_width)
    print(f'\n  {"#":>3}  {"ATTRIBUTE":<{attr_width}}  DESCRIPTION')
    print(f'  {"─" * 3}  {"─" * attr_width}  {"─" * max(12, width - attr_width - 12)}')
    for number, item in enumerate(records, 1):
        attr = str(item.get('attr', ''))
        description = ' '.join(str(item.get('description') or 'No description provided.').split())
        available = max(24, width - attr_width - 12)
        lines = textwrap.wrap(description, width=available) or ['No description provided.']
        print(f'  {number:>3}  {blue}{attr:<{attr_width}}{reset}  {lines[0]}')
        for line in lines[1:]:
            print(f'       {" " * attr_width}  {line}')
    if limit < total:
        print(f'\nShowing the first {limit} results. Use --limit N to change this.')



def print_package_info(records, query, limit=50):
    exact = [item for item in records if item.get('attr') == query or item.get('pname') == query]
    selected = exact or records[:max(0, limit)]
    if not selected:
        print('No matching packages.')
        return
    for item in selected:
        attr = item.get('attr') or query
        print(f"\\n{attr} — {item.get('description') or 'No description available.'}")
        for label, key in [('Name', 'pname'), ('Version', 'version'), ('License', 'license'),
                           ('Homepage', 'homepage'), ('Source', 'position'),
                           ('Main program', 'mainProgram'), ('Programs', 'programs'),
                           ('Platforms', 'platforms')]:
            value = item.get(key)
            if value:
                print(f"{label}: {', '.join(map(str, value)) if isinstance(value, list) else value}")
        if item.get('longDescription'):
            print(f"Details: {item['longDescription']}")
        print(f"Try: nix shell nixpkgs#{attr}")
        print(f"Install: nixpkger install {attr}")


def print_option_results(records):
    if not records:
        print('No matching NixOS options.')
        return
    for item in records:
        print(f"\\n{item['name']}")
        if item.get('description'):
            print(f"  {item['description']}")
        for label, key in [('Type', 'type'), ('Default', 'default'),
                           ('Example', 'example'), ('Declared in', 'declarations')]:
            value = item.get(key)
            if value is not None and value != '' and value != []:
                rendered = ', '.join(map(str, value)) if isinstance(value, list) else str(value)
                print(f'  {label}: {rendered}')
        print(f"  Docs: https://search.nixos.org/options?query={quote(item['name'])}")


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
        run(command, env=nix_environment(self.args.allow_unfree))

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
            if self.args.options:
                results = search_options(self.args.query, self.args.limit)
                if self.args.json:
                    print(json.dumps(results))
                else:
                    print_option_results(results)
                return
            if not self.args.query.startswith('soltros.'):
                try:
                    records = search_nixos(self.args.query, self.args.allow_unfree)
                    if self.args.json:
                        print(json.dumps(records))
                    elif self.args.info:
                        print_package_info(records, self.args.query, self.args.limit)
                    else:
                        print_search_results(records, self.args.query, self.args.limit)
                    return
                except (subprocess.SubprocessError, OSError, ValueError, TypeError) as error:
                    if self.args.json:
                        print(f'Elasticsearch search unavailable; falling back to Nix: {error}', file=sys.stderr)
            if self.args.json:
                query = self.args.query
                if query.startswith('soltros.'):
                    query = query[len('soltros.'):]
                    source = 'github:soltros/soltros_nixpkgs'
                else:
                    source = 'nixpkgs'
                command = [*NIX, 'search', '--json']
                if self.args.allow_unfree:
                    command.append('--impure')
                command += [source, '--', query or '^']
                result = json.loads(run(command, capture_output=True, text=True, env=nix_environment(self.args.allow_unfree)).stdout)
                records = []
                for attribute, details in sorted(result.items()):
                    details = dict(details)
                    details['attr'] = attribute.split('.', 3)[-1] if attribute.startswith('legacyPackages.') else attribute
                    records.append(details)
                print(json.dumps(records))
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


def migrate_to_package():
    """Remove only a launcher produced by the legacy installer, never arbitrary files."""
    launcher = Path.home() / '.local' / 'bin' / 'nixpkger'
    if not launcher.exists() and not launcher.is_symlink():
        print(f'Legacy launcher not found: {launcher}')
        return
    if launcher.is_symlink() or not launcher.is_file():
        raise ConfigError(f'Refusing to remove unexpected launcher: {launcher}')
    source = launcher.read_text(encoding='utf-8')
    legacy_dir = str(Path.home() / '.local' / 'share' / 'nixpkger')
    if not (source.startswith('#!/usr/bin/env python3\\nimport runpy\\nimport sys\\n')
            and 'runpy.run_path(' in source and legacy_dir in source
            and 'nixpkger' in source):
        raise ConfigError(f'Refusing to remove launcher not recognized as a legacy Nixpkger install: {launcher}')
    launcher.unlink()
    print(f'Removed legacy launcher: {launcher}')
    print('JSON settings and application data were preserved.')
    print('Install nixpkger through soltros_nixpkgs and refresh your shell command cache if needed.')


def configuration_wizard(settings):
    if not sys.stdin.isatty():
        raise ConfigError('The configuration wizard requires an interactive terminal. Use config --set-flake PATH[#HOST].')
    current = settings.get('flake', '')
    answer = input(f'Flake directory or flake.nix [{current}]: ').strip() or current
    if not answer:
        raise ConfigError('A flake directory is required.')
    path, separator, host = answer.partition('#')
    if not separator:
        host = input('NixOS host name (optional): ').strip()
    settings['flake'] = normalize_flake(path + ('#' + host if host else ''))
    write_settings(settings)
    print('Saved default flake to JSON configuration:')
    print(json.dumps(settings, indent=2, sort_keys=True))


def main(argv=None, *, default_flake=None, default_impure=False):
    args = parser(default_flake, default_impure).parse_args(argv)
    try:
        if args.migrate_to_package:
            if args.action is not None:
                raise ConfigError('--migrate-to-package cannot be combined with a command.')
            migrate_to_package()
            return 0
        if args.action is None:
            parser(default_flake, default_impure).error('a command is required')
        if args.action == 'config':
            if sum(bool(item) for item in (args.set_flake, args.unset_flake, args.wizard)) > 1:
                raise ConfigError('Choose only one of --wizard, --set-flake, or --unset-flake.')
            settings = read_settings()
            if args.wizard:
                configuration_wizard(settings)
                return 0
            if args.set_flake:
                settings['flake'] = normalize_flake(args.set_flake)
                write_settings(settings)
            elif args.unset_flake:
                settings.pop('flake', None)
                write_settings(settings)
            print(json.dumps(settings, indent=2, sort_keys=True))
            return 0
        if args.action == 'self-update':
            self_update(__version__)
            return 0
        if args.flake is None:
            args.flake = read_settings().get('flake')
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
            if args.flake is None:
                args.flake = read_settings().get('flake')
            argv = absolute_location_options(sys.argv[1:], args)
            # GUI clients authorize sudo before invoking mutations. Never block
            # waiting for a terminal password that the client cannot display.
            os.execvp('sudo', ['sudo', '-n', '--', sys.executable, str(Path(__file__).resolve().parent.parent / 'main.py'), *argv])
        except (ConfigError, OSError) as error:
            print(f'nixpkger: {error}', file=sys.stderr)
            return 1
    return main()
