from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache


def run(cmd, timeout=5):
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]}: timed out"
    except OSError as e:
        return 1, "", str(e)


@lru_cache(maxsize=None)
def have(tool):
    return shutil.which(tool) is not None


def user_shell():
    return os.environ.get("SHELL") or shutil.which("bash") or "/bin/sh"


def shell_name():
    return os.path.basename(user_shell())


def shell_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def shell_query(snippet, timeout=5):
    sh = user_shell()
    if shell_name() in ("bash", "zsh", "sh", "dash", "ksh"):
        return run([sh, "-ic", snippet], timeout=timeout)
    return run([sh, "-c", snippet], timeout=timeout)
