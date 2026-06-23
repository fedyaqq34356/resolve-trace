from __future__ import annotations

import os

from . import probes


def trace_command(cmd):
    typ = probes.resolve_type(cmd)
    paths = probes.which_all(cmd)
    path = paths["primary"]

    record = {
        "command": cmd,
        "type": typ,
        "paths": paths,
        "binary_kind": probes.binary_kind(path),
        "shebang": probes.read_shebang(path) if path else None,
        "symlink_target": None,
        "package": probes.package_owner(path) if path else {"available": False},
        "override": probes.overrides(cmd, path),
        "env": probes.env_for(cmd),
        "services": probes.services_for(cmd),
        "context": probes.exec_context(),
    }
    if path and os.path.islink(path):
        record["symlink_target"] = os.path.realpath(path)
    record["diagnosis"] = diagnose(record)
    return record


def diagnose(r):
    cmd = r["command"]
    kind = r["type"]["kind"]
    paths = r["paths"]
    lines = []

    if kind == "not found":
        return f"'{cmd}' resolves to nothing — not an alias, function, builtin, or a file on PATH."

    if kind == "alias":
        lines.append(f"'{cmd}' is a shell alias; the alias body runs before any binary.")
    elif kind == "function":
        lines.append(f"'{cmd}' is a shell function from your rc files; its body runs instead of a binary.")
    elif kind == "builtin":
        lines.append(f"'{cmd}' is a shell builtin, handled by the shell itself.")
    elif kind == "keyword":
        lines.append(f"'{cmd}' is a shell keyword.")
    elif kind == "file":
        bk = r["binary_kind"]
        if bk == "script":
            lines.append(f"'{cmd}' runs the script at {paths['primary']} ({r['shebang']}).")
        elif bk == "symlink":
            lines.append(f"'{cmd}' is a symlink {paths['primary']} -> {r['symlink_target']}.")
        else:
            lines.append(f"'{cmd}' runs the binary at {paths['primary']}.")

    if paths.get("shadowed"):
        lines.append("PATH has multiple matches; the first wins, the rest are shadowed (" +
                     ", ".join(paths["matches"][1:]) + ").")

    pkg = r.get("package", {})
    if pkg.get("package"):
        src = f" — {pkg['source']}" if pkg.get("source") else ""
        lines.append(f"Provided by {pkg['package']} via {pkg['manager']}{src}.")
    elif pkg.get("available") and paths.get("primary"):
        lines.append("No package owns this file; likely hand-installed or from a script/venv.")

    for layer in r.get("override", {}).get("layers", []):
        name = layer["layer"]
        if name == "flatpak":
            lines.append(f"A flatpak provides '{cmd}' too ({layer['ref']}); a wrapper may redirect to it.")
        elif name == "snap":
            lines.append(f"A snap '{cmd}' exists; snap PATH ordering may win.")
        elif name == "container":
            lines.append(f"Inside a container ({layer['ref']}); this is the container's binary, not the host's.")
        elif name == "nix":
            lines.append("Served from /nix/store; the active nix profile/generation controls this version.")
        elif name == "home-manager":
            lines.append("Comes from a nix/home-manager profile; edit the HM config, not /usr.")
        elif name == "user-dir":
            lines.append(f"Lives in a user-writable dir ({layer['ref']}); it overrides the system copy.")

    if "LD_PRELOAD" in r.get("env", {}):
        lines.append("LD_PRELOAD is set; libraries are force-injected, behavior may be altered.")

    svc = r.get("services", {})
    if svc.get("matches"):
        units = ", ".join(m["unit"] for m in svc["matches"])
        lines.append(f"Related service(s): {units}.")

    if r["context"].get("sudo"):
        lines.append("Under sudo; env may be sanitized (secure_path), so PATH differs from your shell.")

    return " ".join(lines) if lines else f"'{cmd}' resolves normally with no overrides detected."
