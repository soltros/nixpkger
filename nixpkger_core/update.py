"""Self-update nixpkger from the project's latest GitHub release."""
from io import BytesIO
import json
import re
from pathlib import Path
import subprocess
import tarfile
import tempfile
from urllib.request import Request, urlopen

RELEASE_URL = 'https://api.github.com/repos/soltros/nixpkger/releases/latest'


def _version(value):
    match = re.search(r'(\d+(?:\.\d+)+)', value or '')
    return tuple(int(part) for part in match.group(1).split('.')) if match else (0,)


def self_update(current_version, opener=urlopen, runner=subprocess.run):
    request = Request(RELEASE_URL, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'nixpkger'})
    with opener(request, timeout=12) as response:
        release = json.loads(response.read().decode('utf-8'))
    tag = release.get('tag_name', '')
    latest = tag.lstrip('v')
    archive_url = release.get('tarball_url')
    if not latest or not archive_url:
        raise RuntimeError('GitHub returned an incomplete latest-release record.')
    if _version(latest) <= _version(current_version):
        print(f'nixpkger {current_version} is up to date.')
        return False

    print(f'Updating nixpkger {current_version} -> {latest}...')
    archive_request = Request(archive_url, headers={'User-Agent': 'nixpkger'})
    with opener(archive_request, timeout=30) as response:
        archive = response.read()
    with tempfile.TemporaryDirectory(prefix='nixpkger-update-') as directory:
        root = Path(directory)
        with tarfile.open(fileobj=BytesIO(archive), mode='r:gz') as bundle:
            for member in bundle.getmembers():
                target = (root / member.name).resolve()
                if root.resolve() not in target.parents:
                    raise RuntimeError('The latest release archive contains an unsafe path.')
            bundle.extractall(root)
        source = next((path for path in root.iterdir() if (path / 'install.sh').is_file()), None)
        if source is None:
            raise RuntimeError('The latest release archive did not contain install.sh.')
        runner(['sh', str(source / 'install.sh'), str(source)], check=True)
    print(f'Updated nixpkger to {latest}.')
    return True
