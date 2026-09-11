# nixpkger

Manage NixOS packages from the command line. nixpkger edits your package module,
backs it up, and rebuilds the system. It supports channels, local flakes, and
packages from [soltros_nixpkgs](https://github.com/soltros/soltros_nixpkgs).

Written in Python. Requires Python 3.9 or newer and the NixOS command-line tools.
No extra Python packages are needed.

## Install

Download and extract the source archive from the
[latest release](https://github.com/soltros/nixpkger/releases/latest), then run
`sh install.sh` inside the extracted directory. To install from Git:

```sh
git clone https://github.com/soltros/nixpkger.git
cd nixpkger
sh install.sh
```

The program goes in `~/.local/share/nixpkger`, with a launcher in `~/.local/bin`.
Add that directory to your `PATH` if needed:

```sh
export PATH="$HOME/.local/bin:$PATH"
nixpkger --version
```

Put the `export` line in your shell's startup file to keep it across sessions.
Set `NIXPKGER_PREFIX` to use a different installation prefix. The installer
uses the checkout or extracted archive and does not change your Nix profile.
You can also run `./nixpkger` directly from the source directory.

## Set up a package module

If you already have `apps.nix`, keep it. Otherwise, create a module like this:

```nix
{ config, pkgs, ... }:
{
  environment.systemPackages = with pkgs; [
    firefox
    git
  ];
}
```

For a channel configuration, save it as `/etc/nixos/apps.nix` and add
`./apps.nix` to the `imports` list in `/etc/nixos/configuration.nix`.
For a flake, put it in your configuration tree and import it from the selected
host's modules. nixpkger edits an existing package module; finding a file does
not automatically add it to your NixOS configuration.

## Install, remove, and search

```sh
nixpkger install firefox git
nixpkger remove git
nixpkger search firefox
nixpkger search --limit 20 firefox
nixpkger search --json firefox
nixpkger list
nixpkger self-update
```

`list` shows the packages declared in the selected module. Package names are
Nix attributes, such as `firefox` or `python3Packages.pip`.

Regular nixpkgs searches use the Elasticsearch service behind
[search.nixos.org](https://search.nixos.org/packages), returning rich package
metadata quickly. If that service is unavailable, nixpkger falls back to the
local Nix evaluator. `search --json` emits a JSON array of structured records
for GUI clients, including `attr`, `pname`, `version`, `description`, long
description, license, platforms, programs, and optional homepage/source
position fields. It searches `nixpkgs` by default and also accepts the
`soltros.` prefix used by the built-in soltros source.

Human-readable results are ranked, numbered, aligned, colorized on interactive
terminals, and wrapped to the terminal width. Use `--limit N` to control the
number shown; JSON output remains structured for programmatic clients.

Pass `--allow-unfree` before the command to include unfree packages during
search and NixOS rebuild evaluation. This uses Nixpkgs' `NIXPKGS_ALLOW_UNFREE`
setting and `--impure` for the evaluation that needs it.
An unchanged package list does not trigger a rebuild.

Commands that write files or change the system request sudo. Search, list,
help, and version run as your user. `python3 main.py` runs with the current
user's privileges and does not request sudo itself.

`self-update` checks the latest GitHub release, downloads its source archive,
and runs the bundled installer only when a newer version is available. It does
not modify your NixOS configuration or package modules.

## Packages from soltros_nixpkgs

Use the `soltros.` prefix:

```sh
nixpkger search soltros.
nixpkger search soltros.water
nixpkger install soltros.termsmith soltros.waterfox
nixpkger remove soltros.waterfox
nixpkger update --source soltros
```

The source is built in. You do not need to add an overlay or edit `flake.nix`.
Ordinary names such as `git` use your configuration's `pkgs`; prefixed names
use the repository's package outputs for your host platform.

The first install saves a repository revision and content hash in a marked
block in the package module. Later installs reuse it. Run
`update --source soltros` to move that module to the current repository revision
and rebuild. Search uses the latest repository, so a newly added package may
need a source update before it can be installed.

These packages use the repository's locked nixpkgs and package policy.
Their pin is separate from your system's `flake.lock`. Each category has its
own pin. Removing all soltros packages leaves the pin for later use.
Keep the marked block intact; automatic integration requires a module argument
set containing `pkgs`, as shown above.

Installing a package does not enable its companion NixOS services. For Pantheon
Studio's desktop integration, follow the module instructions in its repository.

## Flakes and file locations

Put global options before the command:

```sh
nixpkger --flake ~/my-nixos#desktop install soltros.termsmith
nixpkger --flake ~/my-nixos/flake.nix#desktop --impure update
nixpkger --config-dir ~/my-nixos list
```

`--flake` accepts a local directory or `flake.nix`, optionally followed by
`#HOST`. nixpkger searches that directory recursively for `apps.nix`.
Without a flake, it searches `/etc/nixos`. Use `--config-dir` to choose another
search directory, including one outside the flake.

If several files match, nixpkger lists them and asks you to select one:

```sh
nixpkger --flake ~/my-nixos#desktop \
  --apps-file hosts/desktop/modules/apps.nix install soltros.termsmith

nixpkger --flake ~/my-nixos#desktop \
  --apps-file /another/location/packages.nix list
```

`--apps-file` accepts any filename. Relative module paths are based on the
search directory. Relative flake paths are based on your working directory,
or on `--config-dir` when you supply it. `#HOST` selects the rebuild target;
it does not choose between package files.

The file options also apply to removal, backups, snapshots, restore, and source
updates. A system flake update does not require choosing a package file.
Git metadata, backups, and common cache directories are excluded from searches.
Symlinked files work; symlinked directories are not searched.

## Categories

```sh
nixpkger add-category tools
nixpkger install --category tools git soltros.termsmith
nixpkger remove --category tools git
nixpkger list-categories tools.nix
nixpkger update --source soltros --category tools
```

`add-category` creates a package module and adds its import to the discovered
`configuration.nix`. Category files live in `categories/` beside that file.
Use `--module-file hosts/desktop/default.nix` to choose a different importing
module. For channel rebuilds, that option also selects the NixOS entry module.

Installing into a category alone does not add its import. For Git-backed flakes,
create a category module using the example above and stage it with Git before
running `add-category`. Nix excludes untracked files from those flakes;
nixpkger does not stage files for you.

## Updates and recovery

```sh
nixpkger update
nixpkger snapshot
nixpkger backup
nixpkger restore /path/to/snapshot.nix
nixpkger gc
```

Channel updates run `nixos-rebuild switch --upgrade`. Flake updates run
`nix flake update` in the selected flake directory, then rebuild. A failed flake
update or rebuild restores the previous lock file. Channel changes are not
rolled back. nixpkger enables the Nix experimental features its commands need.

Before changing a module, nixpkger checks its Nix syntax and saves the old file
in `app_backups` under the search directory. Replacements are atomic and preserve
existing ownership and permissions. If the write or rebuild fails, it restores
the previous files. A failed activation may still have changed part of the
running system; restoring source files is not a system-generation rollback.

Snapshots go in `app_snapshots`. Snapshot, backup, and restore cover the selected
package module, including its soltros pin, but not the whole configuration.
Restore keeps the source snapshot and backs up the file it replaces.

`gc` runs `nix-collect-garbage -d`. This deletes old generations as well as
collecting garbage.

## Supported Nix syntax

Automatic edits require one
`environment.systemPackages = with pkgs; [ ... ];` assignment containing plain
package attributes. Comments and unrelated text are preserved. Complex package
expressions, interpolated strings, and indented strings are rejected; edit those
modules manually. Category imports require a simple list of literal paths.

Syntax checks happen before writes; evaluation and package availability are
checked by the rebuild. A file lock serializes nixpkger commands using the same
configuration directory. Other editors do not use that lock. Power loss or a
forced process kill can interrupt a change. ACLs and extended file attributes
are not copied during replacement.

## Upgrading from v3

Install the new version and replace any old `~/scripts/nixpkger` alias or PATH
entry with `~/.local/bin/nixpkger`. Keep your existing Nix modules.

Flake and impure modes now use `--flake` and `--impure`. You no longer need to
replace `main.py`. The old variant filenames remain compatibility entry points
in the source tree.

Category removal is now noninteractive, matching ordinary removal. Invalid
arguments return an error. `update` updates the system configuration; it no
longer runs the old `nix-env -u` profile update.

See [the v4.0.0 release notes](docs/releases/v4.0.0.md) for the full change list.

## Development

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
git diff --check
```

Tests use temporary files and mocked system commands. With Nix installed, they
also parse generated modules and evaluate source bindings against a local stub.
CI runs the suite on Python 3.9, 3.13, and 3.14.

For a live repository search and Termsmith derivation evaluation:

```sh
python3 tests/check_live_source.py
```

That check requires network and Nix daemon access. It does not build packages
or activate a system configuration.
