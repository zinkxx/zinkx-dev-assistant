import subprocess
from pathlib import Path


def get_changed_files(repo_path: str) -> list[str]:
    repo = Path(repo_path)
    if not (repo / ".git").exists():
        return []

    try:
        cmd = "git status --porcelain"
        r = subprocess.run(
            ["bash", "-lc", f"cd '{repo_path}' && {cmd}"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return []

        files: list[str] = []
        for line in r.stdout.splitlines():
            if not line:
                continue
            # format: XY path
            path = line[3:].strip()
            full = repo / path
            if full.exists() and full.is_file():
                files.append(str(full))

        return files
    except Exception:
        return []
