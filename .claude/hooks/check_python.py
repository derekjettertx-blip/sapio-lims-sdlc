#!/usr/bin/env python
"""
PostToolUse hook: verify a Python edit didn't break anything.

Runs after Claude edits or writes a file. For .py files under webhooks/ or
server.py it runs three checks, cheapest first, and exits 2 (blocking) on the
first failure so the error is fed back to Claude to fix immediately:

  1. py_compile        - syntax errors in the edited file
  2. ruff              - real bug rules only (E9,F); undefined names, bad
                         f-strings, redefinitions. Style rules are NOT enabled.
  3. import            - imports the edited module, then server.py. The second
                         is the important one: server.py imports every
                         registered handler, so it catches breakage this edit
                         caused ELSEWHERE, not just in the file itself.

Anything else (non-Python, outside the scope dirs, missing venv) exits 0 and
gets out of the way. The hook never blocks on its own failure to run.

Total cost is roughly 1s warm. See .claude/settings.json for the wiring.
"""
import json
import os
import subprocess
import sys
from typing import NoReturn

# Ruff rules: E9 (syntax/IO errors) + F (pyflakes: undefined names, imports,
# f-strings, redefinitions). F401 unused-import and F841 unused-variable are
# ignored because the repo has 3 pre-existing occurrences that would otherwise
# block every edit to those files. Remove the ignores once those are cleaned up.
RUFF_SELECT = "E9,F"
RUFF_IGNORE = "F401,F841"

# Generated file (~62k lines): syntax and import checks still apply, but linting
# it is meaningless and reports thousands of hits.
SKIP_RUFF = {"data_type_models.py"}

TIMEOUT = 90


def fail(message: str) -> NoReturn:
    """Block the tool call and hand the reason back to Claude."""
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(2)


def skip() -> NoReturn:
    """Nothing to do, or we can't run - never block on our own account."""
    sys.exit(0)


def missing_module(result: "subprocess.CompletedProcess", name: str) -> bool:
    """
    True if the subprocess failed because `name` isn't installed.

    Needed because `python -m <missing>` exits 1 - the same code ruff uses for
    "violations found". Without this, a developer who hasn't installed the dev
    dependencies would be blocked on every single edit.
    """
    return f"No module named {name}" in (result.stderr or "") or (
        f"No module named '{name}'" in (result.stderr or "")
    )


def find_repo_root(start: str):
    """Walk up from the edited file to the directory holding server.py + webhooks/."""
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.isfile(os.path.join(d, "server.py")) and os.path.isdir(
            os.path.join(d, "webhooks")
        ):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def find_python(repo_root: str):
    """
    Locate the project interpreter. Checked in order:
      1. .venv inside the repo      - the usual layout for a fresh clone
      2. .venv beside the repo      - this workspace's layout (see CLAUDE.md)
      3. whatever is running us     - last resort; verified below before use
    """
    for base in (repo_root, os.path.dirname(repo_root)):
        for rel in ("Scripts/python.exe", "bin/python"):
            candidate = os.path.join(base, ".venv", *rel.split("/"))
            if os.path.isfile(candidate):
                return candidate
    return sys.executable


def module_name(repo_root: str, path: str):
    """webhooks/OnSave/Foo.py -> webhooks.OnSave.Foo ; server.py -> server"""
    rel = os.path.relpath(path, repo_root)
    if rel.startswith(".."):
        return None
    return os.path.splitext(rel)[0].replace(os.sep, "/").replace("/", ".")


def run(argv, cwd):
    return subprocess.run(
        argv, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT, check=False
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        # Malformed or absent payload - not our place to complain.
        skip()

    path = (payload.get("tool_input") or {}).get("file_path")
    if not isinstance(path, str):
        skip()
    if not path or not path.endswith(".py") or not os.path.isfile(path):
        skip()
    path = os.path.abspath(path)

    repo_root = find_repo_root(path)
    if repo_root is None:
        skip()

    # Scope: only live code - webhooks/ and server.py. Skips kb/ templates and
    # anything outside the repo.
    in_webhooks = path.startswith(os.path.join(repo_root, "webhooks") + os.sep)
    is_server = path == os.path.join(repo_root, "server.py")
    if not (in_webhooks or is_server):
        skip()

    python = find_python(repo_root)
    if python is None:
        sys.stderr.write(
            "check_python hook: no .venv found next to the repo - skipping checks.\n"
        )
        skip()

    rel = os.path.relpath(path, repo_root)

    # 1. Syntax.
    result = run([python, "-m", "py_compile", path], repo_root)
    if result.returncode != 0:
        fail(f"Syntax error in {rel}:\n{result.stderr or result.stdout}")

    # 2. Lint (bug rules only).
    if os.path.basename(path) not in SKIP_RUFF:
        result = run(
            [
                python, "-m", "ruff", "check", path,
                "--select", RUFF_SELECT,
                "--ignore", RUFF_IGNORE,
                "--output-format", "concise",
                "--no-cache",
            ],
            repo_root,
        )
        # A missing module also exits 1, identical to "violations found" - so
        # check for that first or a dev without ruff gets blocked on every edit.
        if missing_module(result, "ruff"):
            sys.stderr.write(
                "check_python hook: ruff is not installed, skipping the lint step.\n"
                "Install it with:  python -m pip install -r requirements.txt\n"
            )
        elif result.returncode == 1:
            fail(f"Ruff found problems in {rel}:\n{result.stdout or result.stderr}")

    # 3. Imports - the edited module, then the whole registered server graph.
    #    server.py imports every registered handler, so this is what catches
    #    breakage the edit caused in OTHER files.
    mod = module_name(repo_root, path)
    stmts = "import server"
    if mod and mod != "server":
        stmts = f"import {mod}; import server"
    result = run([python, "-c", stmts], repo_root)
    if result.returncode != 0:
        # Distinguish "this environment was never set up" from "the edit broke
        # something". Blocking on the former would be a false positive.
        for dep in ("sapiopylib", "sapiopycommons", "waitress", "flask"):
            if missing_module(result, dep):
                sys.stderr.write(
                    f"check_python hook: {dep} is not installed, skipping the "
                    f"import check.\nInstall with:  python -m pip install -r requirements.txt\n"
                )
                skip()
        tail = "\n".join((result.stderr or result.stdout).strip().splitlines()[-12:])
        fail(
            f"Import check failed after editing {rel}.\n"
            f"This means the edit broke {rel} or something that imports it:\n{tail}"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
