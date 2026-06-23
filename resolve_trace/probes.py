from __future__ import annotations

import grp
import os
import pwd
import stat

from .util import have, run, shell_name, shell_query, shell_quote, user_shell

SUSPICIOUS_ENV = {
    "PATH": "command lookup order",
    "LD_PRELOAD": "forces shared libraries into every binary",
    "LD_LIBRARY_PATH": "overrides where libraries load from",
    "LD_AUDIT": "loads an auditing library into the dynamic linker",
    "PYTHONPATH": "injects modules ahead of the stdlib",
    "PYTHONHOME": "relocates the Python install",
    "PYTHONSTARTUP": "runs code at interpreter start",
    "PERL5LIB": "injects Perl modules",
    "RUBYLIB": "injects Ruby libraries",
    "NODE_OPTIONS": "passes flags to every node process",
    "NODE_PATH": "changes node module resolution",
    "GIT_SSH": "swaps the ssh binary git uses",
    "BROWSER": "overrides which browser is launched",
    "EDITOR": "overrides the default editor",
    "VISUAL": "overrides the default editor",
    "PAGER": "overrides the default pager",
    "SHELL": "interactive shell",
    "MANPATH": "where man pages are searched",
    "XDG_DATA_DIRS": "affects desktop/flatpak app resolution",
    "VIRTUAL_ENV": "active Python virtualenv",
    "CONDA_PREFIX": "active conda environment",
    "GTK_PATH": "loads GTK modules",
    "QT_PLUGIN_PATH": "loads Qt plugins",
}


def resolve_type(cmd):
    out = {"name": cmd, "kind": "not found", "detail": None}
    q = shell_quote(cmd)
    sep = "\x1f"

    if shell_name() == "zsh":
        rc, raw, _ = shell_query(f"whence -w -- {q}; printf '{sep}'; whence -v -- {q}")
        kind_raw, _, detail = raw.partition(sep)
        kind = kind_raw.strip().split(":")[-1].strip()
        kind = {"command": "file", "hashed": "file", "reserved": "keyword",
                "none": ""}.get(kind, kind)
    else:
        rc, raw, _ = shell_query(f"type -t -- {q}; printf '{sep}'; type -- {q}")
        kind_raw, _, detail = raw.partition(sep)
        kind = kind_raw.strip()

    if kind:
        out["kind"] = kind
    if detail.strip():
        out["detail"] = detail.strip()
    return out


def which_all(cmd):
    matches = []
    seen = set()
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        p = os.path.join(d, cmd)
        if p in seen:
            continue
        seen.add(p)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            matches.append(p)
    return {
        "primary": matches[0] if matches else None,
        "matches": matches,
        "shadowed": len(matches) > 1,
    }


def read_shebang(path):
    try:
        with open(path, "rb") as f:
            head = f.read(128)
    except OSError:
        return None
    if head.startswith(b"#!"):
        return head.split(b"\n", 1)[0][2:].decode("utf-8", "replace").strip()
    return None


def binary_kind(path):
    if path is None:
        return None
    if os.path.islink(path):
        return "symlink"
    shebang = read_shebang(path)
    if shebang:
        return "script"
    rc, out, _ = run(["file", "-b", path])
    if rc == 0 and "ELF" in out:
        return "elf binary"
    return "file"


def pacman_source(name):
    rc, _, _ = run(["pacman", "-Qm", name])
    if rc == 0:
        return "AUR / local (foreign package)"
    rc, out, _ = run(["pacman", "-Si", name])
    if rc == 0:
        for line in out.splitlines():
            if line.startswith("Repository"):
                return "official repo: " + line.split(":", 1)[1].strip()
    return "official repo"


def rpm_source(name):
    if have("dnf"):
        rc, out, _ = run(["dnf", "repoquery", "--installed", "--qf",
                          "%{from_repo}", name])
        repo = out.strip().splitlines()[0] if rc == 0 and out.strip() else ""
        if repo and repo != "@System":
            return f"repo: {repo}"
    return "installed rpm"


def package_owner(path):
    res = {"manager": None, "package": None, "source": None, "available": False}
    if not path:
        return res
    real = os.path.realpath(path)
    targets = (path,) if real == path else (path, real)

    if have("pacman"):
        res["available"] = True
        res["manager"] = "pacman"
        for target in targets:
            rc, out, _ = run(["pacman", "-Qo", target])
            if rc == 0 and " is owned by " in out:
                owner = out.strip().split(" is owned by ")[-1]
                res["package"] = owner.strip()
                res["source"] = pacman_source(owner.split()[0])
                return res
        return res

    if have("rpm"):
        res["available"] = True
        res["manager"] = "rpm/dnf" if have("dnf") else "rpm"
        for target in targets:
            rc, out, _ = run(["rpm", "-qf", target])
            if rc == 0 and "not owned" not in out:
                name = out.strip().splitlines()[0]
                res["package"] = name
                res["source"] = rpm_source(name)
                return res
        return res

    if have("dpkg"):
        res["available"] = True
        res["manager"] = "dpkg"
        for target in targets:
            rc, out, _ = run(["dpkg", "-S", target])
            if rc == 0 and out.strip():
                res["package"] = out.strip().split(":")[0]
                res["source"] = "apt repo"
                return res
        return res

    return res


def overrides(cmd, path):
    found = []

    if have("flatpak"):
        rc, out, _ = run(["flatpak", "list", "--columns=application,name"])
        if rc == 0:
            low = cmd.lower()
            for line in out.splitlines():
                if low in line.lower():
                    found.append({"layer": "flatpak", "ref": line.strip()})

    if have("snap"):
        rc, out, _ = run(["snap", "list"])
        if rc == 0:
            for line in out.splitlines()[1:]:
                parts = line.split()
                if parts and parts[0] == cmd:
                    found.append({"layer": "snap", "ref": parts[0]})

    container = None
    if os.path.exists("/run/.containerenv"):
        container = "podman/toolbox"
    elif os.path.exists("/run/.toolboxenv"):
        container = "toolbox"
    elif os.environ.get("container"):
        container = os.environ["container"]
    if container:
        found.append({"layer": "container", "ref": container})

    if path:
        real = os.path.realpath(path)
        home = os.path.expanduser("~")
        if "/nix/store" in real:
            found.append({"layer": "nix", "ref": real})
        if "/.nix-profile/" in path or "/etc/profiles/per-user/" in path:
            found.append({"layer": "home-manager", "ref": path})
        for d in (f"{home}/.local/bin", f"{home}/bin", "/usr/local/bin"):
            if path.startswith(d + "/"):
                found.append({"layer": "user-dir", "ref": d})
                break

    return {"layers": found, "any": bool(found)}


def env_for(cmd):
    return {var: {"value": os.environ[var], "why": why}
            for var, why in SUSPICIOUS_ENV.items() if var in os.environ}


def suspicious_env():
    hits = env_for(None)
    parts = os.environ.get("PATH", "").split(os.pathsep)
    notes = []
    if "" in parts or "." in parts:
        notes.append("PATH contains '.' or an empty entry (cwd in PATH)")
    home = os.path.expanduser("~")
    if "/usr/bin" in parts:
        sysidx = parts.index("/usr/bin")
        for i, d in enumerate(parts[:sysidx]):
            if d.startswith(home) or d.startswith("/tmp"):
                notes.append(f"writable dir '{d}' precedes /usr/bin in PATH")
    return {"vars": hits, "path_notes": notes, "path": os.environ.get("PATH", "")}


def init_system():
    comm = ""
    try:
        with open("/proc/1/comm") as f:
            comm = f.read().strip()
    except OSError:
        pass
    if comm == "systemd":
        return "systemd"
    if os.path.isdir("/run/openrc"):
        return "openrc"
    if comm == "runit" or os.path.isdir("/run/runit"):
        return "runit"
    if comm.startswith("s6"):
        return "s6"
    if comm == "dinit":
        return "dinit"
    if comm == "init":
        return "sysvinit/openrc"
    return comm or "unknown"


def _nonsystemd_services(cmd):
    found = []
    candidates = {
        "openrc": ["/etc/init.d"],
        "runit": ["/etc/sv", "/etc/runit/sv"],
        "s6": ["/etc/s6", "/etc/s6-rc/source"],
        "dinit": ["/etc/dinit.d"],
    }
    for kind, dirs in candidates.items():
        for d in dirs:
            p = os.path.join(d, cmd)
            if os.path.exists(p):
                found.append({"scope": kind, "unit": p})
    return found


def services_for(cmd):
    res = {"init": init_system(), "systemd": have("systemctl"), "matches": []}
    if have("systemctl"):
        for scope in ("--system", "--user"):
            rc, out, _ = run(["systemctl", scope, "list-units", "--type=service",
                              "--all", "--no-legend", "--plain"])
            if rc != 0:
                continue
            for line in out.splitlines():
                parts = line.split()
                if parts and cmd in parts[0]:
                    res["matches"].append({
                        "scope": "user" if scope == "--user" else "system",
                        "unit": parts[0],
                    })
    else:
        res["matches"] = _nonsystemd_services(cmd)
    return res


def lsm_context(path):
    out = {"selinux": None, "apparmor": None}
    rc, ls, _ = run(["ls", "-Zd", path])
    if rc == 0 and ls.strip():
        first = ls.split()[0]
        if ":" in first and first.count(":") >= 2:
            out["selinux"] = first
    if os.path.exists("/sys/kernel/security/apparmor"):
        out["apparmor"] = "enabled"
        if path:
            base = os.path.basename(path)
            profile = os.path.join("/etc/apparmor.d", base)
            if os.path.exists(profile):
                out["apparmor"] = f"profile present ({profile})"
    return out


def file_info(path):
    info = {"path": path, "exists": False}
    if not os.path.lexists(path):
        return info
    info["exists"] = True
    info["realpath"] = os.path.realpath(path)
    info["symlink"] = os.path.islink(path)
    if info["symlink"]:
        info["link_target"] = os.readlink(path)

    try:
        st = os.stat(path)
    except OSError:
        st = os.lstat(path)
    info["mode"] = stat.filemode(st.st_mode)
    info["executable"] = bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    info["setuid"] = bool(st.st_mode & stat.S_ISUID)
    info["setgid"] = bool(st.st_mode & stat.S_ISGID)
    info["size"] = st.st_size
    try:
        info["owner"] = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        info["owner"] = str(st.st_uid)
    try:
        info["group"] = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        info["group"] = str(st.st_gid)

    rc, out, _ = run(["file", "-b", path])
    info["type"] = out.strip() if rc == 0 else None
    info["kind"] = binary_kind(path)
    info["shebang"] = read_shebang(path)
    info["lsm"] = lsm_context(path)
    info["package"] = package_owner(path)
    return info


def exec_context():
    ctx = {
        "uid": os.getuid(),
        "euid": os.geteuid(),
        "user": pwd.getpwuid(os.getuid()).pw_name,
        "shell": user_shell(),
        "init": init_system(),
        "sudo": bool(os.environ.get("SUDO_USER")),
        "sudo_from": os.environ.get("SUDO_USER"),
        "root": os.geteuid() == 0,
        "ssh": bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY")),
        "container": None,
        "tty": None,
    }
    if os.path.exists("/run/.containerenv"):
        ctx["container"] = "podman/toolbox"
    elif os.environ.get("container"):
        ctx["container"] = os.environ["container"]
    try:
        ctx["tty"] = os.ttyname(0)
    except OSError:
        ctx["tty"] = None
    return ctx
