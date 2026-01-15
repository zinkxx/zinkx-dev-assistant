from pathlib import Path
import os
import stat


def install_precommit_hook(repo_path: str):
    repo = Path(repo_path)
    git_dir = repo / ".git"
    hooks_dir = git_dir / "hooks"

    if not hooks_dir.exists():
        raise RuntimeError("Not a git repository")

    hook_file = hooks_dir / "pre-commit"

    script = f"""#!/bin/bash
source "{Path.home()}/Projects/zinkx-dev-assistant/.venv/bin/activate"
python "{repo / 'src' / 'precommit_runner.py'}"
"""

    hook_file.write_text(script, encoding="utf-8")

    # executable yap
    hook_file.chmod(hook_file.stat().st_mode | stat.S_IEXEC)

    return hook_file
