from __future__ import annotations


def _kv(label, value, width=10):
    return f"{label + ':':<{width}} {value}"


def render_trace(r):
    out = [_kv("Command", r["command"]), _kv("Type", r["type"]["kind"])]

    paths = r["paths"]
    if paths.get("primary"):
        suffix = f" ({r['binary_kind']})" if r.get("binary_kind") else ""
        out.append(_kv("Path", paths["primary"] + suffix))
    if r.get("symlink_target"):
        out.append(_kv("Target", r["symlink_target"]))
    if r.get("shebang"):
        out.append(_kv("Shebang", r["shebang"]))
    for p in paths.get("matches", [])[1:]:
        out.append(_kv("Shadowed", p))

    pkg = r.get("package", {})
    if pkg.get("package"):
        out.append(_kv("Package", f"{pkg['package']} [{pkg['manager']}]"))
        if pkg.get("source"):
            out.append(_kv("Source", pkg["source"]))
    elif pkg.get("available"):
        out.append(_kv("Package", "none (not owned by any package)"))
    else:
        out.append(_kv("Package", "n/a (no package manager)"))

    ov = r.get("override", {})
    if ov.get("any"):
        for layer in ov["layers"]:
            out.append(_kv("Override", f"{layer['layer']}: {layer['ref']}"))
    else:
        out.append(_kv("Override", "none"))

    for var, info in r.get("env", {}).items():
        val = info["value"]
        if len(val) > 80:
            val = val[:77] + "..."
        out.append(_kv("Env", f"{var}={val}  ({info['why']})"))

    svc = r.get("services", {})
    if svc.get("matches"):
        for m in svc["matches"]:
            out.append(_kv("Service", f"{m['scope']}: {m['unit']}"))

    ctx = r.get("context", {})
    flags = []
    if ctx.get("sudo"):
        flags.append(f"sudo (from {ctx.get('sudo_from')})")
    if ctx.get("root"):
        flags.append("root")
    if ctx.get("container"):
        flags.append(f"container:{ctx['container']}")
    if ctx.get("ssh"):
        flags.append("ssh")
    tail = ("  [" + ", ".join(flags) + "]") if flags else ""
    out.append(_kv("Shell", f"{ctx.get('shell', '?')}  init={ctx.get('init')}{tail}"))

    if r["type"].get("detail") and r["type"]["kind"] in ("alias", "function"):
        out.append("")
        out.append("Definition:")
        out += ["  " + ln for ln in r["type"]["detail"].splitlines()]

    out += ["", "Diagnosis:", "  " + r["diagnosis"]]
    return "\n".join(out)


def render_file(f):
    if not f.get("exists"):
        return f"File: {f['path']}\n  does not exist."

    out = [_kv("File", f["path"], 12)]
    if f.get("kind"):
        out.append(_kv("Kind", f["kind"], 12))
    if f.get("symlink"):
        out.append(_kv("Symlink", f"-> {f.get('link_target')}", 12))
        out.append(_kv("Realpath", f.get("realpath"), 12))
    if f.get("shebang"):
        out.append(_kv("Shebang", f["shebang"], 12))
    if f.get("type"):
        out.append(_kv("Type", f["type"], 12))
    out.append(_kv("Mode", f["mode"], 12))
    out.append(_kv("Owner", f"{f['owner']}:{f['group']}", 12))
    out.append(_kv("Size", f"{f['size']} bytes", 12))

    flags = []
    if f.get("executable"):
        flags.append("executable")
    if f.get("setuid"):
        flags.append("SETUID")
    if f.get("setgid"):
        flags.append("SETGID")
    out.append(_kv("Flags", ", ".join(flags) if flags else "none", 12))

    lsm = f.get("lsm", {})
    if lsm.get("selinux"):
        out.append(_kv("SELinux", lsm["selinux"], 12))
    if lsm.get("apparmor"):
        out.append(_kv("AppArmor", lsm["apparmor"], 12))

    pkg = f.get("package", {})
    if pkg.get("package"):
        out.append(_kv("Package", f"{pkg['package']} [{pkg['manager']}]", 12))
        if pkg.get("source"):
            out.append(_kv("Source", pkg["source"], 12))
    elif pkg.get("available"):
        out.append(_kv("Package", "none (not owned)", 12))

    diag = []
    if f.get("setuid"):
        diag.append("SETUID set — runs as the file owner regardless of caller. Audit carefully.")
    if pkg.get("package"):
        diag.append(f"Installed by {pkg['package']}" +
                    (f" ({pkg['source']})." if pkg.get("source") else "."))
    elif pkg.get("available"):
        diag.append("Not owned by any package — hand-placed or generated.")
    if f.get("symlink"):
        diag.append(f"Symlink; real target is {f.get('realpath')}.")
    if f.get("kind") == "script":
        diag.append("It is a script, not a compiled binary.")

    out += ["", "Diagnosis:", "  " + (" ".join(diag) if diag else "Ordinary file, nothing unusual.")]
    return "\n".join(out)


def render_env(e):
    out = ["Suspicious environment variables:"]
    if not e["vars"]:
        out.append("  (none of the known hijack-capable vars are set)")
    for var, info in e["vars"].items():
        val = info["value"]
        if len(val) > 100:
            val = val[:97] + "..."
        out.append(f"  {var}={val}")
        out.append(f"      ^ {info['why']}")

    if e.get("path_notes"):
        out.append("")
        out.append("PATH warnings:")
        out += [f"  ! {n}" for n in e["path_notes"]]

    danger = [v for v in ("LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH") if v in e["vars"]]
    out.append("")
    out.append("Diagnosis:")
    if danger or e.get("path_notes"):
        out.append("  Active overrides: " + ", ".join(danger + e.get("path_notes", [])) + ".")
    else:
        out.append("  Environment looks clean for command resolution.")
    return "\n".join(out)
