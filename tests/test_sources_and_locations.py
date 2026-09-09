import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from nixpkger_core.cli import Application, main, parser
from nixpkger_core.config import ConfigError, TEMPLATE, edit_packages, packages
from nixpkger_core.locations import absolute_location_options, find_module
from nixpkger_core.sources import (BEGIN, END, SOLTROS, current_reference,
                                  enable_source, pinned_reference, source_block)


def metadata(revision='a' * 40):
    return subprocess.CompletedProcess([], 0, stdout=json.dumps({'locked': {
        'type': 'github', 'owner': 'soltros', 'repo': 'soltros_nixpkgs',
        'rev': revision, 'narHash': 'sha256-' + 'A' * 43 + '=',
    }}))


class SourceTests(unittest.TestCase):
    def test_namespace_and_pin_preserve_packages(self):
        run = Mock(return_value=metadata())
        source = edit_packages(TEMPLATE, ['git', 'soltros.termsmith'])
        edited = enable_source(source, run)
        self.assertEqual(packages(edited), ['git', 'soltros.termsmith'])
        self.assertIn('packages.${pkgs.stdenv.hostPlatform.system}', edited)
        self.assertIn(SOLTROS + '/' + 'a' * 40, current_reference(edited))
        self.assertEqual(enable_source(edited, run), edited)
        run.assert_called_once()

    def test_refresh_replaces_only_pin(self):
        first = enable_source(TEMPLATE, Mock(return_value=metadata()))
        refreshed = enable_source(first, Mock(return_value=metadata('b' * 40)), refresh=True)
        self.assertEqual(refreshed, first.replace('a' * 40, 'b' * 40))
        self.assertEqual(refreshed.count(BEGIN), 1)

    def test_metadata_validation(self):
        for data in ({}, {'locked': {'rev': 'evil"${foo}', 'narHash': 'sha256-x'}}):
            with self.subTest(data=data), self.assertRaises(ConfigError):
                pinned_reference(Mock(return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(data))))

    def test_manual_binding_not_overwritten(self):
        source = TEMPLATE.replace(':', ': let soltros = {}; in', 1)
        with self.assertRaises(ConfigError):
            enable_source(source, Mock())

    def test_modified_marker_refused(self):
        source = enable_source(TEMPLATE, Mock(return_value=metadata()))
        for bad in (source.replace('stdenv', 'other'), source + '\n' + END,
                    source.replace(BEGIN, '# unrelated')):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                current_reference(bad)

    def test_no_pkgs_argument_refused(self):
        with self.assertRaises(ConfigError):
            enable_source(TEMPLATE.replace('config, pkgs,', 'config,'), Mock())

    @unittest.skipUnless(shutil.which('nix-instantiate'), 'Nix unavailable')
    def test_generated_binding_evaluates_with_stub_source(self):
        source = enable_source(edit_packages(TEMPLATE, ['soltros.termsmith']), Mock(return_value=metadata()))
        # Replace only the fetching primitive to exercise generated Nix scoping offline.
        source = source.replace('builtins.getFlake', '(_: { packages.x86_64-linux.termsmith = "works"; })')
        expression = f'({source}) {{ pkgs.stdenv.hostPlatform.system = "x86_64-linux"; config = {{}}; }}'
        result = subprocess.run(['nix-instantiate', '--eval', '--strict', '--json', '--expr', expression],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['environment']['systemPackages'], ['works'])


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'flake.nix').write_text('{}')
        self.apps = self.root / 'hosts/desktop/modules/apps.nix'
        self.apps.parent.mkdir(parents=True)
        self.apps.write_text(TEMPLATE)

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(['--flake', str(self.root) + '#desktop', *args])

    def test_flake_drives_search_root(self):
        app = Application(parser().parse_args(['--flake', str(self.root) + '#desktop', 'list']))
        self.assertEqual(app.root, self.root)
        self.assertEqual(app.apps, self.apps)
        self.assertEqual(app.flake_ref, str(self.root) + '#desktop')

    def test_flake_file_path_supported(self):
        app = Application(parser().parse_args(['--flake', str(self.root / 'flake.nix') + '#desktop', 'list']))
        self.assertEqual(app.flake, self.root)
        self.assertEqual(app.apps, self.apps)

    def test_sudo_receives_absolute_locations(self):
        argv = ['--flake=' + str(self.root / 'flake.nix') + '#desktop',
                '--apps-file', 'hosts/desktop/modules/apps.nix', 'install', 'soltros.termsmith']
        normalized = absolute_location_options(argv, parser().parse_args(argv))
        self.assertEqual(normalized, ['--flake', str(self.root) + '#desktop',
                                     '--apps-file', str(self.apps), 'install', 'soltros.termsmith'])

    def test_relative_flake_uses_cwd_without_explicit_root(self):
        with patch('pathlib.Path.cwd', return_value=self.root.parent):
            app = Application(parser().parse_args(['--flake', self.root.name + '#desktop', 'list']))
        self.assertEqual(app.root, self.root)

    def test_nested_hidden_module_discovery(self):
        self.apps.unlink()
        hidden = self.root / '.config/nixos/apps.nix'
        hidden.parent.mkdir(parents=True)
        hidden.write_text(TEMPLATE)
        self.assertEqual(find_module(self.root, 'apps.nix'), hidden)

    def test_ambiguous_modules_fail(self):
        (self.root / 'apps.nix').write_text(TEMPLATE)
        with self.assertRaisesRegex(ConfigError, '--apps-file'):
            find_module(self.root, 'apps.nix')
        self.assertEqual(self.invoke('--apps-file', 'hosts/desktop/modules/apps.nix', 'list'), 0)

    def test_explicit_file_outside_tree_and_custom_name(self):
        app = Application(parser().parse_args(['--flake', str(self.root), '--apps-file', '/tmp/custom-packages.nix', 'list']))
        self.assertEqual(app.apps, Path('/tmp/custom-packages.nix'))

    def test_ignored_backup_trees_and_symlink_deduplication(self):
        old = self.root / 'app_backups/apps.nix'
        old.parent.mkdir()
        old.write_text(TEMPLATE)
        alias = self.root / 'alias/apps.nix'
        alias.parent.mkdir()
        alias.symlink_to(self.apps)
        self.assertEqual(find_module(self.root, 'apps.nix'), self.apps)

    @patch('nixpkger_core.cli.run')
    def test_nested_install_and_rebuild(self, run):
        self.assertEqual(self.invoke('install', 'git'), 0)
        self.assertEqual(packages(self.apps.read_text()), ['git'])
        self.assertEqual(run.call_args.args[0], ['nixos-rebuild', 'switch', '--flake', str(self.root) + '#desktop'])
        self.assertFalse((self.root / 'apps.nix').exists())

    @patch('nixpkger_core.cli.run')
    def test_source_install_refresh_and_remove(self, run):
        run.return_value = metadata()
        self.assertEqual(self.invoke('install', 'soltros.termsmith', 'git'), 0)
        source = self.apps.read_text()
        self.assertEqual(packages(source), ['soltros.termsmith', 'git'])
        self.assertIsNotNone(current_reference(source))
        run.reset_mock()
        self.assertEqual(self.invoke('install', 'soltros.termsmith'), 0)
        run.assert_not_called()
        run.return_value = metadata('b' * 40)
        self.assertEqual(self.invoke('update', '--source', 'soltros'), 0)
        self.assertIn('b' * 40, current_reference(self.apps.read_text()))
        self.assertEqual(self.invoke('remove', 'soltros.termsmith'), 0)
        self.assertEqual(packages(self.apps.read_text()), ['git'])

    @patch('nixpkger_core.cli.run')
    def test_source_failure_does_not_write(self, run):
        run.side_effect = subprocess.CalledProcessError(1, 'nix', stderr='network failed')
        self.assertEqual(self.invoke('install', 'soltros.termsmith'), 1)
        self.assertEqual(self.apps.read_text(), TEMPLATE)

    @patch('nixpkger_core.cli.run')
    def test_failed_source_rebuild_restores_original(self, run):
        run.side_effect = [metadata(), None, subprocess.CalledProcessError(1, 'rebuild')]
        self.assertEqual(self.invoke('install', 'soltros.termsmith'), 1)
        self.assertEqual(self.apps.read_text(), TEMPLATE)

    @patch('nixpkger_core.cli.run')
    def test_search_formats_namespace(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout=json.dumps({
            'packages.x86_64-linux.termsmith': {'description': 'Terminal profiles'},
        }))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['search', 'soltros.term']), 0)
        self.assertIn('soltros.termsmith\tTerminal profiles', output.getvalue())
        self.assertIn(SOLTROS, run.call_args.args[0])

    @patch('nixpkger_core.cli.run')
    def test_flake_update_ignores_module_ambiguity(self, run):
        (self.root / 'apps.nix').write_text(TEMPLATE)
        self.assertEqual(self.invoke('update'), 0)

    @patch('nixpkger_core.cli.run')
    def test_nested_category_import(self, run):
        config = self.root / 'hosts/desktop/configuration.nix'
        config.write_text('{ imports = [ ./modules/apps.nix ]; }')
        self.assertEqual(self.invoke('add-category', 'tools'), 0)
        self.assertTrue((config.parent / 'categories/tools.nix').exists())
        self.assertIn('./categories/tools.nix', config.read_text())

    @patch('nixpkger_core.cli.run')
    def test_external_config_root_with_flake(self, run):
        external = self.root / 'separate'
        external.mkdir()
        (external / 'apps.nix').write_text(TEMPLATE)
        self.assertEqual(self.invoke('--config-dir', str(external), 'install', 'hello'), 0)
        self.assertEqual(packages((external / 'apps.nix').read_text()), ['hello'])
        self.assertEqual(self.apps.read_text(), TEMPLATE)


if __name__ == '__main__':
    unittest.main()
