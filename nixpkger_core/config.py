"""Conservative, source-preserving edits for nixpkger's simple Nix modules."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

TEMPLATE = "{ config, pkgs, ... }:\n{\n  environment.systemPackages = with pkgs; [\n  ];\n}\n"
ATTRIBUTE = re.compile(r"[A-Za-z_][A-Za-z0-9_'-]*(?:\.[A-Za-z_][A-Za-z0-9_'-]*)*")
WORD = re.compile(r"[A-Za-z0-9_./'-]+")


class ConfigError(ValueError):
    """A configuration cannot be safely edited."""


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int


def tokens(source):
    """Skip comments, retain offsets, and treat strings as opaque tokens."""
    result = []
    i = 0
    while i < len(source):
        start = i
        if source[i].isspace():
            i += 1
            continue
        if source[i] == '#':
            end = source.find('\n', i)
            i = len(source) if end == -1 else end
            continue
        if source.startswith('/*', i):
            end = source.find('*/', i + 2)
            if end == -1:
                raise ConfigError('Unterminated Nix comment.')
            i = end + 2
            continue
        if source.startswith("''", i):
            # Interpolation and escaping need a full Nix parser. Refuse safely.
            raise ConfigError('Indented Nix strings are not supported for automatic editing.')
        if source[i] == '<' and re.match(r'<[A-Za-z0-9_./-]+>', source[i:]):
            i = source.index('>', i) + 1
        elif source[i] == '"':
            i += 1
            while i < len(source):
                if source.startswith('${', i):
                    raise ConfigError('Interpolated Nix strings are not supported for automatic editing.')
                if source[i] == '\\':
                    i += 2
                elif source[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ConfigError('Unterminated Nix string.')
        else:
            match = WORD.match(source, i)
            i += len(match[0]) if match else 1
        result.append(Token(source[start:i], start, i))
    return result


def list_span(source, option, prefix=()):
    items = tokens(source)
    matches = [i for i, item in enumerate(items) if item.value == option
               and i + 1 < len(items) and items[i + 1].value == '=']
    if len(matches) != 1:
        raise ConfigError(f'Expected exactly one {option} assignment.')
    start = matches[0] + 2
    expected = [*prefix, '[']
    if [t.value for t in items[start:start + len(expected)]] != expected:
        raise ConfigError(f'Unsupported {option} expression; expected a simple list.')
    opening = start + len(expected) - 1
    closing = next((i for i in range(opening + 1, len(items)) if items[i].value == ']'), None)
    if closing is None or closing + 1 >= len(items) or items[closing + 1].value != ';':
        raise ConfigError(f'Unsupported or unterminated {option} list.')
    return items[opening], items[closing], items[opening + 1:closing]


def package_span(source):
    opening, closing, entries = list_span(source, 'environment.systemPackages', ('with', 'pkgs', ';'))
    if any(not ATTRIBUTE.fullmatch(item.value) or item.value in {'with', 'let', 'in', 'if', 'then', 'else', 'assert', 'rec', 'inherit', 'or'} for item in entries):
        raise ConfigError('Package lists must contain plain package attributes; edit complex expressions manually.')
    return opening, closing, entries


def packages(source):
    return [item.value for item in package_span(source)[2]]


def edit_packages(source, requested, remove=False):
    requested = list(dict.fromkeys(requested))
    if any(not ATTRIBUTE.fullmatch(name) or name in {'with', 'let', 'in', 'if', 'then', 'else', 'assert', 'rec', 'inherit', 'or'} for name in requested):
        raise ConfigError('Package names must be plain Nix attributes, such as firefox or python3Packages.pip.')
    _, closing, entries = package_span(source)
    existing = {entry.value for entry in entries}
    if remove:
        for entry in reversed(entries):
            if entry.value in requested:
                source = source[:entry.start] + source[entry.end:]
        return source
    additions = [name for name in requested if name not in existing]
    if not additions:
        return source
    insertion = '\n' + ''.join(f'    {name}\n' for name in additions) + '  '
    return source[:closing.start] + insertion + source[closing.start:]


def category_path(root, name):
    name = name.removesuffix('.nix')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*', name):
        raise ConfigError('Category names may contain letters, numbers, underscores, and hyphens.')
    return Path(root) / 'categories' / f'{name}.nix'


def edit_import(source, name):
    _, closing, entries = list_span(source, 'imports')
    if any(not re.fullmatch(r'(?:\./|\.\./|/)[A-Za-z0-9_./-]+|<[^<>]+>|"[^"$]+"', item.value) for item in entries):
        raise ConfigError('Imports must be a simple list of literal paths.')
    path = f'./categories/{name}.nix'
    if any(item.value.strip('"') == path for item in entries):
        return source
    return source[:closing.start] + f'\n    {path}\n  ' + source[closing.start:]


def atomic_write(path, content):
    """Replace a complete file, preserving an existing target's owner and mode."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = path.stat() if path.exists() else None
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content)
            stream.flush()
            if metadata:
                os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode) if metadata else 0o644)
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def backup(path, directory, prefix='app_backup'):
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    destination = Path(directory) / f'{prefix}_{stamp}_{uuid.uuid4().hex[:8]}.nix'
    atomic_write(destination, Path(path).read_text(encoding='utf-8'))
    return destination
