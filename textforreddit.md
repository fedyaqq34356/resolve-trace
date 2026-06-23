# Reddit posts

## English

**Title:**
```
rt — a tiny CLI that tells you what actually runs when you type a command
```

**Body:**
```
We've all hit it: "wait, WHICH `python` / `ls` / `firefox` is this?" Is it an alias? A shadowed PATH binary? A flatpak? An AUR build? A nix profile?

I got tired of running `type`, `which`, `pacman -Qo`, `ls -l`, `echo $PATH` one at a time, so I put all of it behind one command:

    rt <command>

It walks every resolution layer and prints a short, grep-able report:

  • alias, function, builtin, script, symlink, or ELF binary
  • the full resolved path, plus PATH shadowing (which copy actually wins)
  • the owning package, and on Arch whether it's an official repo or AUR/foreign
  • override layers: flatpak, snap, podman/toolbox, nix, home-manager, ~/.local/bin
  • env vars that change behavior (LD_PRELOAD, PYTHONPATH, '.' in PATH, and so on)
  • SELinux/AppArmor context, setuid bits, owner
  • related services, systemd or not (openrc/runit/s6/dinit, so Artix works too)

Then it prints a one-line plain-English Diagnosis.

Example:

    $ rt ls
    Type: alias
    Definition: ls is an alias for eza --icons --group-directories-first
    Diagnosis: 'ls' is a shell alias; the alias body runs before any binary.

Subcommands: trace / file / env / snapshot. `--json` works on all of them. If a package manager, init, or LSM is missing, that layer is skipped instead of crashing.

Install (no pipe-to-shell, read it first):

    git clone https://github.com/fedyaqq34356/resolve-trace
    cd resolve-trace
    ./rt pacman          # runs straight from the repo, zero deps

Optional, to get `rt` everywhere:

    ln -s "$PWD/rt" ~/.local/bin/rt

Pure stdlib Python 3.8+, no dependencies, nothing to build. The whole thing is ~400 lines you can skim in two minutes before running anything.

Repo: https://github.com/fedyaqq34356/resolve-trace

I wrote it for my own Arch/Artix boxes. If it breaks or guesses wrong on your distro, tell me, that's exactly the kind of report I want.
```

---

## Русский

**Заголовок:**
```
rt — маленькая CLI, которая показывает что РЕАЛЬНО запускается по команде и откуда оно взялось
```

**Тело:**
```
Знакомо: "стоп, а это какой вообще `python` / `ls` / `firefox`?" Алиас? Перехваченный бинарь из PATH? flatpak? Сборка из AUR? nix-профиль?

Надоело каждый раз руками гонять `type`, `which`, `pacman -Qo`, `ls -l`, `echo $PATH`, поэтому собрал всё в одну команду:

    rt <команда>

Она проходит по всем слоям и печатает короткий отчёт (удобно грепать):

  • alias, функция, builtin, скрипт, симлинк или ELF-бинарник
  • полный путь плюс затенение в PATH (какая копия реально побеждает)
  • пакет-владелец, а на Arch ещё и официальный репо это или AUR/foreign
  • слои перехвата: flatpak, snap, podman/toolbox, nix, home-manager, ~/.local/bin
  • переменные окружения, меняющие поведение (LD_PRELOAD, PYTHONPATH, '.' в PATH и т.д.)
  • контекст SELinux/AppArmor, setuid-биты, владелец
  • связанные сервисы, systemd или нет (openrc/runit/s6/dinit, так что Artix тоже работает)

В конце печатает короткий вывод Diagnosis обычным языком.

Пример:

    $ rt ls
    Type: alias
    Definition: ls is an alias for eza --icons --group-directories-first
    Diagnosis: 'ls' это shell-алиас; тело алиаса выполняется вместо бинарника.

Подкоманды: trace / file / env / snapshot. `--json` есть у всех. Если пакетного менеджера, init или LSM нет, слой просто пропускается, ничего не падает.

Установка (без pipe-to-shell, сначала прочитай код):

    git clone https://github.com/fedyaqq34356/resolve-trace
    cd resolve-trace
    ./rt pacman          # работает прямо из репо, без зависимостей

По желанию, чтобы `rt` был везде:

    ln -s "$PWD/rt" ~/.local/bin/rt

Чистый stdlib Python 3.8+, без зависимостей, ничего собирать не надо. Весь код ~400 строк, можно пробежать глазами за пару минут перед запуском.

Репозиторий: https://github.com/fedyaqq34356/resolve-trace

Писал под свои Arch/Artix. Если у вас на дистрибутиве сломается или соврёт, напишите, такие кейсы мне как раз и нужны.
```

---

## Скриншот

Терминал, три команды подряд: `rt ls` (alias→eza), `rt python` (symlink→3.14), `rt yay` (AUR).
Тёмная тема, окно пошире чтобы строки `Diagnosis:` не переносились.
