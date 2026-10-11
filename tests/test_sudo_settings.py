import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nixpkger_core.settings import mutation_settings


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


if __name__ == '__main__':
    unittest.main()
