import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from nixpkger_core.config import (ConfigError, TEMPLATE, atomic_write, backup,
                                 category_path, edit_import, edit_packages, packages)
from nixpkger_core.cli import main


class EditingTests(unittest.TestCase):
    def test_comments_and_exact_names(self):
        source = TEMPLATE.replace('[\n', '[\n    # git is useful\n    gitFull /* keep */ git\n')
        edited = edit_packages(source, ['git'], remove=True)
        self.assertEqual(packages(edited), ['gitFull'])
        self.assertIn('# git is useful', edited)
        self.assertIn('/* keep */', edited)
        self.assertEqual(packages(edit_packages(edited, ['git', 'git'])), ['gitFull', 'git'])

    def test_noop_is_byte_identical(self):
        source = edit_packages(TEMPLATE, ['git'])
        self.assertEqual(edit_packages(source, ['git']), source)
        self.assertEqual(edit_packages(source, ['absent'], remove=True), source)

    def test_other_lists_untouched(self):
        source = TEMPLATE.replace('  environment', '  imports = [ ./other.nix ];\n  environment')
        self.assertIn('imports = [ ./other.nix ];', edit_packages(source, ['git']))

    def test_fake_assignment_in_string_and_comment(self):
        source = TEMPLATE.replace('  environment', '  description = "environment.systemPackages = with pkgs; [ fake ];";\n  # environment.systemPackages = with pkgs; [ fake ];\n  environment')
        self.assertEqual(packages(edit_packages(source, ['git'])), ['git'])

    def test_unsupported_expressions_refused(self):
        for body in ('(foo.override {})', '[ git ]', 'lib.optionals true [ git ]', '"git"', 'with other; git'):
            with self.subTest(body=body), self.assertRaises(ConfigError):
                edit_packages(TEMPLATE.replace('[\n', '[ ' + body + '\n'), ['hello'])
        with self.assertRaises(ConfigError):
            edit_packages('{}', ['hello'])
        with self.assertRaises(ConfigError):
            edit_packages(TEMPLATE + TEMPLATE, ['hello'])

    def test_injection_rejected(self):
        for value in ('git; evil', '../git', '$(whoami)', 'with', 'foo/bar'):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                edit_packages(TEMPLATE, [value])
        for value in ('../escape', '/etc/passwd', 'x/y', ''):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                category_path('/tmp', value)

    def test_imports_inline_and_comments(self):
        source = '{ imports = [ ./hardware-configuration.nix ]; }'
        edited = edit_import(source, 'tools')
        self.assertIn('./categories/tools.nix', edited)
        self.assertEqual(edit_import(edited, 'tools'), edited)
        commented = '{ imports = [ # ./categories/tools.nix\n ]; }'
        self.assertEqual(edit_import(commented, 'tools').count('./categories/tools.nix'), 2)

    def test_import_expression_refused(self):
        for source in ('{ imports = foo; }', '{ imports = [ (foo {}) ]; }'):
            with self.assertRaises(ConfigError):
                edit_import(source, 'tools')

    def test_import_search_paths_and_quoted_paths(self):
        source = '{ imports = [ <nixpkgs/nixos> "./categories/tools.nix" ]; }'
        self.assertEqual(edit_import(source, 'tools'), source)


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.apps = self.root / 'apps.nix'
        self.apps.write_text(TEMPLATE)

    def test_atomic_write_preserves_mode_and_symlink(self):
        self.apps.chmod(0o640)
        link = self.root / 'link.nix'
        link.symlink_to(self.apps)
        atomic_write(link, 'new')
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.apps.read_text(), 'new')
        self.assertEqual(self.apps.stat().st_mode & 0o777, 0o640)

    def test_failed_replace_preserves_original(self):
        with patch('os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                atomic_write(self.apps, 'new')
        self.assertEqual(self.apps.read_text(), TEMPLATE)
        self.assertEqual(list(self.root.iterdir()), [self.apps])

    def test_backups_unique(self):
        paths = [backup(self.apps, self.root / 'backups') for _ in range(2)]
        self.assertNotEqual(*paths)
        self.assertTrue(all(p.read_text() == TEMPLATE for p in paths))

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(['--config-dir', str(self.root), *args])

    @patch('nixpkger_core.cli.run')
    def test_install_validates_then_rebuilds_and_backs_up(self, run):
        self.assertEqual(self.invoke('install', 'git', 'git'), 0)
        self.assertEqual(packages(self.apps.read_text()), ['git'])
        self.assertEqual(run.call_args_list[0].args[0], ['nix-instantiate', '--parse', '-'])
        self.assertEqual(run.call_args_list[1].args[0], ['nixos-rebuild', 'switch', '-I', f'nixos-config={self.root / "configuration.nix"}'])
        self.assertEqual(next((self.root / 'app_backups').iterdir()).read_text(), TEMPLATE)
        run.reset_mock()
        self.assertEqual(self.invoke('install', 'git'), 0)
        run.assert_not_called()

    @patch('nixpkger_core.cli.run')
    def test_failed_rebuild_rolls_back(self, run):
        run.side_effect = [None, subprocess.CalledProcessError(1, 'nixos-rebuild')]
        self.assertEqual(self.invoke('install', 'git'), 1)
        self.assertEqual(self.apps.read_text(), TEMPLATE)

    @patch('nixpkger_core.cli.run', side_effect=subprocess.CalledProcessError(1, 'parse'))
    def test_parse_failure_does_not_write(self, run):
        self.assertEqual(self.invoke('install', 'git'), 1)
        self.assertEqual(self.apps.read_text(), TEMPLATE)
        self.assertFalse((self.root / 'app_backups').exists())

    @patch('nixpkger_core.cli.run')
    def test_restore_preserves_source_and_backs_up_previous_config(self, run):
        snapshot = self.root / 'snapshot.nix'
        snapshot.write_text(edit_packages(TEMPLATE, ['hello']))
        self.assertEqual(self.invoke('restore', str(snapshot)), 0)
        self.assertEqual(snapshot.read_text(), self.apps.read_text())
        self.assertEqual(next((self.root / 'app_backups').iterdir()).read_text(), TEMPLATE)

    @patch('nixpkger_core.cli.run')
    def test_search_and_gc_without_apps(self, run):
        self.apps.unlink()
        self.assertEqual(self.invoke('search', 'hello'), 0)
        self.assertEqual(run.call_args.args[0], ['nix-env', '-qa', '--', 'hello'])
        self.assertEqual(self.invoke('gc'), 0)
        self.assertEqual(run.call_args.args[0], ['nix-collect-garbage', '-d'])

    @patch('nixpkger_core.cli.run')
    def test_category_created_and_imported(self, run):
        config = self.root / 'configuration.nix'
        config.write_text('{ imports = [ ./hardware-configuration.nix ]; }')
        self.assertEqual(self.invoke('add-category', 'tools'), 0)
        self.assertEqual(category_path(self.root, 'tools.nix').read_text(), TEMPLATE)
        self.assertIn('./categories/tools.nix', config.read_text())
        run.reset_mock()
        self.assertEqual(self.invoke('add-category', 'tools'), 0)
        run.assert_not_called()

    @patch('nixpkger_core.cli.run')
    def test_category_creation_rolled_back(self, run):
        config = self.root / 'configuration.nix'
        old = '{ imports = []; }'
        config.write_text(old)
        run.side_effect = [None, None, subprocess.CalledProcessError(1, 'rebuild')]
        self.assertEqual(self.invoke('add-category', 'tools'), 1)
        self.assertEqual(config.read_text(), old)
        self.assertFalse(category_path(self.root, 'tools').exists())

    @patch('nixpkger_core.cli.run')
    def test_remove_missing_category_does_not_create_it(self, run):
        self.assertEqual(self.invoke('remove', '--category', 'missing', 'git'), 1)
        self.assertFalse((self.root / 'categories').exists())
        run.assert_not_called()

    @patch('nixpkger_core.cli.run')
    def test_flake_update_and_impure_rebuild(self, run):
        (self.root / 'flake.nix').write_text('{}')
        self.assertEqual(self.invoke('--flake', '.#host', '--impure', 'update'), 0)
        self.assertEqual(run.call_args_list[0].args[0], ['nix', 'flake', 'update'])
        self.assertEqual(run.call_args_list[0].kwargs['cwd'], self.root)
        self.assertIn('extra-experimental-features = nix-command flakes', run.call_args_list[0].kwargs['env']['NIX_CONFIG'])
        self.assertEqual(run.call_args_list[1].args[0], ['nixos-rebuild', 'switch', '--flake', f'{self.root}#host', '--impure'])

    @patch('nixpkger_core.cli.run')
    def test_failed_flake_update_restores_lock(self, run):
        (self.root / 'flake.nix').write_text('{}')
        lock = self.root / 'flake.lock'
        lock.write_text('original')
        def fail(*args, **kwargs):
            lock.write_text('changed')
            raise subprocess.CalledProcessError(1, 'update')
        run.side_effect = fail
        self.assertEqual(self.invoke('--flake', '.', 'update'), 1)
        self.assertEqual(lock.read_text(), 'original')

    def test_invalid_arguments(self):
        for args in ([], ['install'], ['install', '--category'], ['unknown']):
            with self.subTest(args=args), self.assertRaises(SystemExit) as error:
                self.invoke(*args)
            self.assertEqual(error.exception.code, 2)

    def test_version_without_configuration(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as error:
            main(['--version'])
        self.assertEqual(error.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), 'nixpkger 4.0.0')

    @patch('nixpkger_core.cli.run', side_effect=FileNotFoundError('missing tool'))
    def test_missing_tool_reports_failure(self, run):
        self.assertEqual(self.invoke('search', 'git'), 1)

    @patch('nixpkger_core.cli.run')
    def test_channel_update_does_not_require_apps(self, run):
        self.apps.unlink()
        self.assertEqual(self.invoke('update'), 0)
        self.assertEqual(run.call_args.args[0][-1], '--upgrade')

    @patch('nixpkger_core.cli.run')
    def test_new_flake_lock_removed_on_failure(self, run):
        (self.root / 'flake.nix').write_text('{}')
        lock = self.root / 'flake.lock'
        def fail(*args, **kwargs):
            lock.write_text('new')
            raise subprocess.CalledProcessError(1, 'update')
        run.side_effect = fail
        self.assertEqual(self.invoke('--flake', '.', 'update'), 1)
        self.assertFalse(lock.exists())

    def test_install_and_installed_launcher(self):
        repo = Path(__file__).resolve().parent.parent
        prefix = self.root / "install space ' quote"
        result = subprocess.run(['sh', str(repo / 'install.sh'), str(repo)],
                                env={**os.environ, 'NIXPKGER_PREFIX': str(prefix)},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(prefix / 'bin/nixpkger'), '--config-dir',
                                 str(self.root), 'list'], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No packages declared.', result.stdout)


@unittest.skipUnless(shutil.which('nix-instantiate'), 'Nix is not installed')
class NixIntegrationTests(unittest.TestCase):
    def test_generated_modules_parse_with_real_nix(self):
        source = TEMPLATE.replace('[\n', '[\n # comment\n gitFull /* note */ git\n')
        for edited in (edit_packages(source, ['hello', 'python3Packages.pip']),
                       edit_packages(source, ['git'], remove=True),
                       edit_import('{ imports = [ ./hardware-configuration.nix ]; }', 'tools')):
            completed = subprocess.run(['nix-instantiate', '--parse', '-'], input=edited,
                                       text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__':
    unittest.main()
