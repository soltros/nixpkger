"""Built-in package sources, pinned in the module that uses them."""
import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .config import ConfigError, tokens

SOLTROS = 'github:soltros/soltros_nixpkgs'
NIX = ['nix', '--extra-experimental-features', 'nix-command flakes']
BEGIN = '# nixpkger: begin soltros source'
END = '# nixpkger: end soltros source'
REFERENCE = re.compile(re.escape(SOLTROS) + r'/[0-9a-f]{40}\?narHash=sha256-[A-Za-z0-9%_-]+')
NIXOS_SEARCH_URL = 'https://search.nixos.org/backend/latest-51-nixos-26.05/_search'
NIXOS_SEARCH_AUTH = 'Basic YVdWU0FMWHBadjpYOGdQSG56TDUyd0ZFZWt1eHNmUTljU2g='


def pinned_reference(run):
    metadata = json.loads(run([*NIX, 'flake', 'metadata', '--json', SOLTROS],
                              capture_output=True, text=True).stdout)
    locked = metadata.get('locked', {})
    revision, digest = locked.get('rev', ''), locked.get('narHash', '')
    if (locked.get('type') != 'github' or locked.get('owner') != 'soltros'
            or locked.get('repo') != 'soltros_nixpkgs'
            or not re.fullmatch(r'[0-9a-f]{40}', revision)
            or not re.fullmatch(r'sha256-[A-Za-z0-9+/]{43}=', digest)):
        raise ConfigError('Nix returned invalid lock metadata for the soltros repository.')
    return f'{SOLTROS}/{revision}?narHash={quote(digest, safe="")}'


def header_end(source):
    items = tokens(source)
    if not items or items[0].value != '{':
        raise ConfigError('Source integration requires a module starting with { ..., pkgs, ... }:')
    closing = next((i for i, item in enumerate(items) if item.value == '}'), None)
    if (closing is None or closing + 1 >= len(items) or items[closing + 1].value != ':'
            or 'pkgs' not in [item.value for item in items[1:closing]]
            or any(item.value == '{' for item in items[1:closing])):
        raise ConfigError('Source integration requires a simple module argument set containing pkgs.')
    return items[closing + 1].end


def source_block(reference):
    if not REFERENCE.fullmatch(reference):
        raise ConfigError('Invalid pinned soltros flake reference.')
    return (f'{BEGIN}\nlet\n'
            f'  soltros = (builtins.getFlake "{reference}").packages.${{pkgs.stdenv.hostPlatform.system}};\n'
            f'in\n{END}')


def current_reference(source):
    if BEGIN not in source and END not in source:
        return None
    match = re.search(re.escape(BEGIN) + r'.*?' + re.escape(END), source, re.DOTALL)
    references = REFERENCE.findall(match[0]) if match else []
    if (not match or source.count(BEGIN) != 1 or source.count(END) != 1
            or len(references) != 1 or match[0] != source_block(references[0])
            or source[header_end(source):match.start()].strip()):
        raise ConfigError('The managed soltros source block was modified; restore it before updating.')
    return references[0]


def enable_source(source, run, refresh=False):
    previous = current_reference(source)
    if previous and not refresh:
        return source
    if previous:
        return source.replace(source_block(previous), source_block(pinned_reference(run)), 1)
    end = header_end(source)
    if any(item.value == 'soltros' for item in tokens(source)):
        raise ConfigError('This module already defines soltros; rename that binding before enabling the built-in source.')
    return source[:end] + '\n' + source_block(pinned_reference(run)) + '\n' + source[end:]


def search_soltros(query, run):
    command = [*NIX, 'search', '--json', SOLTROS]
    # Nix search uses regular expressions; keep that behavior, including an empty query.
    result = json.loads(run([*command, '--', query or '^'], capture_output=True, text=True).stdout)
    for attribute, details in sorted(result.items()):
        name = attribute.split('.', 2)[-1]
        description = details.get('description', '').replace('\n', ' ')
        print(f'soltros.{name}\t{description}')
    if not result:
        print('No soltros packages matched.')


def search_nixos(query, allow_unfree=False, opener=urlopen):
    """Search the Elasticsearch index used by search.nixos.org."""
    payload = {
        'from': 0, 'size': 100,
        'query': {'multi_match': {
            'query': query.strip(),
            'fields': ['package_attr_name^9', 'package_programs^9',
                       'package_mainProgram^9', 'package_pname^6',
                       'package_description^1.3', 'package_longDescription'],
            'type': 'best_fields', 'fuzziness': 'AUTO',
        }},
    }
    request = Request(NIXOS_SEARCH_URL, data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json',
                               'Authorization': NIXOS_SEARCH_AUTH}, method='POST')
    with opener(request, timeout=12) as response:
        document = json.loads(response.read().decode('utf-8'))
    records = []
    for hit in document.get('hits', {}).get('hits', []):
        item = hit.get('_source', {})
        licenses = item.get('package_license') or []
        records.append({
            'attr': item.get('package_attr_name', ''),
            'pname': item.get('package_pname', ''),
            'version': item.get('package_pversion', ''),
            'description': item.get('package_description', ''),
            'longDescription': item.get('package_longDescription', ''),
            'homepage': item.get('package_homepage', []),
            'position': item.get('package_position'),
            'license': ', '.join(x.get('fullName', x.get('shortName', '')) for x in licenses),
            'platforms': item.get('package_platforms', []),
            'programs': item.get('package_programs', []),
            'mainProgram': item.get('package_mainProgram', ''),
        })
    return records
