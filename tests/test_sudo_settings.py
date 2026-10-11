import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nixpkger_core.settings import mutation_settings
from nixpkger_core.cli import Application, parser


class SudoSettingsTests(unittest.TestCase):
    def test_sudo_uses_invoking_users_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / '.config' / 'nixpkger' / 'config.json'
            config.parent.mkdir(parents=True)
            expected = {'flake': str(home / 'nixos-config') + '#i3-1315u',
                        'branch': 'laptop_plasma'}
            config.write_text(json.dumps(expected))
            with patch.dict(os.environ, {'SUDO_UID': '1234'}), \
                 patch('nixpkger_core.settings.os.geteuid', return_value=0), \
                 patch('nixpkger_core.settings.pwd.getpwuid') as user:
                user.return_value.pw_dir = str(home)
                self.assertEqual(mutation_settings(), expected)
                user.assert_called_once_with(1234)

    def test_normal_invocation_uses_own_settings(self):
        with patch('nixpkger_core.settings.os.geteuid', return_value=1000), \
             patch('nixpkger_core.settings.read_settings', return_value={'branch': 'main'}):
            self.assertEqual(mutation_settings(), {'branch': 'main'})

    def test_install_prep_runs_pull_then_flake_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'flake.nix').write_text('{}')
            args = parser().parse_args(['--flake', str(root) + '#testhost', 'install', 'firefox'])
            args.expected_branch = 'main'
            app = Application(args)
            calls = []
            def fake_run(command, **kwargs):
                calls.append(command)
                if 'rev-parse' in command:
                    return type('Completed', (), {'stdout': 'origin/main\\n'})()
                return type('Completed', (), {'stdout': ''})()
            with patch('nixpkger_core.cli.verify_branch'), \
                 patch('nixpkger_core.cli.run', side_effect=fake_run), \
                 patch('nixpkger_core.cli.os.geteuid', return_value=1000):
                app.prepare_flake_install()
            self.assertTrue(any('pull' in command and '--ff-only' in command for command in calls))
            self.assertTrue(any(command[-2:] == ['flake', 'update'] for command in calls))
            self.assertLess(next(i for i, command in enumerate(calls) if 'pull' in command),
                            next(i for i, command in enumerate(calls) if command[-2:] == ['flake', 'update']))


if __name__ == '__main__':
    unittest.main()
