# resolve-trace (`rt`)

![python](https://img.shields.io/badge/python-3.8%2B-blue)
![deps](https://img.shields.io/badge/dependencies-none-brightgreen)
![license](https://img.shields.io/badge/license-GPLv3-blue)
![platform](https://img.shields.io/badge/platform-Linux-lightgrey)

A small Linux CLI that explains **what actually runs** when you type a command,
**where it comes from**, and **why** it might behave differently than you expect.

It walks every resolution layer: shell aliases/functions, PATH ordering, the
owning package (and on Arch whether it's an **official repo** or **AUR** build),
alternate-delivery layers (flatpak / snap / podman-toolbox / nix / home-manager),
related systemd or non-systemd services, file permissions and LSM context
(SELinux / AppArmor), and the environment variables that quietly change behavior.

Stdlib-only Python 3.8+. No dependencies. Every layer degrades gracefully: a
missing package manager, missing systemd (Artix/OpenRC, runit, s6, dinit), or
missing tool is skipped, not fatal.

## Demo

```console
$ rt ls
Command:   ls
Type:      alias
Path:      /usr/bin/ls (elf binary)
Package:   coreutils 9.11-1 [pacman]
Source:    official repo: system
Override:  none
Shell:     /bin/zsh  init=openrc

Definition:
  ls is an alias for eza --icons --group-directories-first

Diagnosis:
  'ls' is a shell alias; the alias body runs before any binary.
  Provided by coreutils 9.11-1 via pacman — official repo: system.

$ rt yay
Command:   yay
Type:      file
Path:      /usr/bin/yay (elf binary)
Package:   yay 12.6.0-1 [pacman]
Source:    AUR / local (foreign package)
Diagnosis:
  'yay' runs the binary at /usr/bin/yay. Provided by yay 12.6.0-1
  via pacman — AUR / local (foreign package).

$ rt python
Command:   python
Type:      file
Path:      /usr/bin/python (symlink)
Target:    /usr/bin/python3.14
Package:   python 3.14.5-1 [pacman]
Source:    official repo: system
Diagnosis:
  'python' is a symlink /usr/bin/python -> /usr/bin/python3.14.
```

## Run it

After download, the short launcher is `rt`:

```sh
./rt pacman
./rt trace firefox
./rt file /usr/bin/ls
./rt env
./rt snapshot
```

`rt <name>` with no subcommand is shorthand for `rt trace <name>`.

## Install

### Automatic

One command — clones (if needed), links `rt` onto your PATH, checks Python:

```sh
curl -fsSL https://raw.githubusercontent.com/fedyaqq34356/resolve-trace/main/install.sh | sh
```

or, if you already cloned the repo:

```sh
./install.sh
```

### Manual

```sh
git clone https://github.com/fedyaqq34356/resolve-trace
cd resolve-trace
chmod +x rt
ln -s "$PWD/rt" ~/.local/bin/rt          # make `rt` global
# ensure ~/.local/bin is on PATH:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

Or install as a package (gives global `rt` and `resolve-trace`):

```sh
pipx install .
```

## Commands

```
rt <name>              shorthand for `trace <name>`
rt trace <cmd>         full breakdown of a command
rt file <path>         what a file is, where it came from, who owns it
rt env                 suspicious environment variables
rt snapshot [-o FILE]  dump current system state to a report
```

Global: `--json` on any command for machine output. `--version`.
`trace` also takes `--no-log` to skip the history log.

## Example

```
$ rt pacman
Command:   pacman
Type:      file
Path:      /usr/bin/pacman (elf binary)
Package:   pacman 7.1.0-2 [pacman]
Source:    official repo: system
Override:  none
Shell:     /bin/zsh  init=openrc

Diagnosis:
  'pacman' runs the binary at /usr/bin/pacman. Provided by pacman via
  pacman — official repo: system.
```

## What it inspects

- `type` / `whence` via your interactive shell (bash vs zsh handled), so
  rc-defined aliases and functions are visible.
- alias / function / builtin / external binary / **script** (shebang) / symlink.
- PATH contents, shadowing, writable dirs before system dirs.
- Package owner via **pacman**, **rpm/dnf**, or **dpkg**.
  - Arch: official repo vs **AUR / foreign** (`pacman -Qm`), repo name via `-Si`.
  - Fedora: package + `from_repo` via `dnf repoquery`.
- Override layers: flatpak, snap, podman/toolbox containers, **nix store**,
  **home-manager** profiles, user-writable `~/.local/bin`.
- Services: systemd `--system` and `--user`; on non-systemd inits it reports the
  detected init (**openrc / runit / s6 / dinit**) and matching service dirs.
- File: mode, owner, exec/setuid/setgid bits, symlink target, `file(1)` type,
  **SELinux** context and **AppArmor** profile where present.
- Context: sudo, root, container, ssh, tty, init system.

## How to test

Developer (from the repo):

```sh
./rt trace ls           # an aliased command
./rt trace pacman       # an official-repo binary
./rt trace yay          # an AUR package (if installed)
./rt file /usr/bin/ls   # a real file
./rt env                # your environment
./rt snapshot -o /tmp/state.txt
./rt pacman --json | python3 -m json.tool   # JSON is valid
```

Smoke-test all subcommands at once:

```sh
for c in "trace ls" "trace pacman" env "file /usr/bin/ls" snapshot; do
  echo "== rt $c =="; ./rt $c; echo
done
```

A normal user who just cloned it from GitHub:

```sh
git clone <repo-url> resolve-trace
cd resolve-trace
python3 --version          # need 3.8+
./rt pacman                # run directly, no install, no deps
```

If `./rt` isn't executable after clone: `chmod +x rt`.
To get `rt` everywhere: `ln -s "$PWD/rt" ~/.local/bin/rt` (ensure `~/.local/bin`
is on PATH) — then run `rt firefox` from anywhere.

There are no third-party dependencies, so there is nothing to `pip install` to
run it. `pipx install .` is only for getting a packaged global command.

## Platform notes

- **Fedora**: dnf / rpm / flatpak, systemd.
- **Arch**: pacman (+ AUR detection) / flatpak.
- **Artix and other non-systemd**: init auto-detected (openrc/runit/s6/dinit);
  systemd queries are skipped and service dirs are scanned instead.
- Missing managers, inits, or LSMs are skipped, never fatal.

## Bonus

- `--json` everywhere.
- History log per `trace` at
  `${XDG_STATE_HOME:-~/.local/state}/resolve-trace/history.log` (`--no-log` off).
- fzf integration — pick a command on PATH and trace it:

  ```sh
  compgen -c | sort -u | fzf | xargs rt trace
  ```

## Non-goals

Not a GUI. Not a monolithic "system doctor". It never auto-repairs anything;
diagnosis and action stay separate by design.

## Running the tests

```sh
python3 -m unittest discover -s tests -v
```

Pure stdlib, no test framework to install.

## Contributing

Bug reports and distro edge cases are welcome, especially output from package
managers, inits, or LSMs I cannot test locally. Open an issue with the command
you ran and the full `rt` output (`--json` is ideal).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
