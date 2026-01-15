from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config import load_config
from ipc import write_status   # 👈 progress IPC


# --------------------------------------------------
# Scan modes
# --------------------------------------------------
SCAN_DEV = "dev"
SCAN_PROD = "prod"

# --------------------------------------------------
# File handling
# --------------------------------------------------
TEXT_EXTS = {
    ".php", ".js", ".ts", ".vue", ".html", ".css",
    ".json", ".md", ".py", ".env", ".yml", ".yaml",
    ".ini", ".conf",
}

IGNORE_DIRS = {
    ".git", "vendor", ".venv",
    "dist", "build", ".next", ".nuxt",
    ".idea", ".vscode", "__pycache__", ".pytest_cache",
}

# --------------------------------------------------
# Security patterns
# --------------------------------------------------
SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]+['\"]", re.I),
    re.compile(r"(api[_-]?key|secret|token|password)\s*:\s*['\"][^'\"]+['\"]", re.I),
]

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
)

IGNORE_FILE_MARKER = "@zinkx-ignore-security"


# --------------------------------------------------
# Models
# --------------------------------------------------
@dataclass
class Finding:
    kind: str            # RISK | TODO | INFO
    title: str
    detail: str
    path: str
    line: int | None = None


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def _is_ignored_dir(p: Path, cfg) -> bool:
    if cfg.get("ignore_node_modules", True) and "node_modules" in p.parts:
        return True
    return any(part in IGNORE_DIRS for part in p.parts)


def _safe_read_text(path: Path, limit_bytes: int = 400_000) -> str:
    try:
        if path.stat().st_size > limit_bytes:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _emit_progress(percent: int, mode: str):
    """
    UI için progress IPC
    """
    write_status({
        "type": "progress",
        "percent": percent,
        "mode": mode,
    })


# --------------------------------------------------
# Main scanner
# --------------------------------------------------
def scan_project(
    root: str,
    mode: str = SCAN_DEV,
    only_files: list[str] | None = None,
) -> list[Finding]:

    cfg = load_config()

    ignore_markers = tuple(cfg.get("ignore_inline_markers", []))
    progress_steps = cfg.get("scan_progress_steps", [20, 50, 80, 100])
    show_progress = cfg.get("show_scan_progress", True)

    rootp = Path(root).expanduser().resolve()
    findings: list[Finding] = []

    if not rootp.exists() or not rootp.is_dir():
        return findings

    # --------------------------------------------------
    # File iterator
    # --------------------------------------------------
    if only_files:
        file_iter = [Path(p) for p in only_files if Path(p).is_file()]
    else:
        file_iter = list(rootp.rglob("*"))

    total_files = len(file_iter) or 1
    next_progress_index = 0

    def update_progress(done: int):
        nonlocal next_progress_index
        if not show_progress:
            return
        percent = int((done / total_files) * 100)
        if next_progress_index < len(progress_steps):
            if percent >= progress_steps[next_progress_index]:
                _emit_progress(progress_steps[next_progress_index], mode)
                next_progress_index += 1

    # --------------------------------------------------
    # 1️⃣ .env git ignore check
    # --------------------------------------------------
    if cfg.get("ignore_env", True):
        env_file = rootp / ".env"
        if env_file.exists():
            gitignore = rootp / ".gitignore"
            gi = _safe_read_text(gitignore) if gitignore.exists() else ""
            if ".env" not in gi:
                findings.append(Finding(
                    "RISK",
                    ".env may be tracked",
                    "Project has .env but .gitignore does not mention it.",
                    str(env_file),
                ))

    # --------------------------------------------------
    # 2️⃣ File scanning
    # --------------------------------------------------
    for idx, p in enumerate(file_iter, start=1):
        update_progress(idx)

        if p.is_dir():
            continue
        if _is_ignored_dir(p, cfg):
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue

        text = _safe_read_text(p)
        if not text:
            continue

        if IGNORE_FILE_MARKER in text:
            continue

        lines = text.splitlines()

        # ----------------------------------------------
        # TODO / FIXME
        # ----------------------------------------------
        for i, line in enumerate(lines, start=1):
            low = line.lower()
            if any(m in low for m in ignore_markers):
                continue

            if "todo" in low or "fixme" in low:
                findings.append(Finding(
                    "TODO",
                    "TODO/FIXME found",
                    line.strip()[:240],
                    str(p),
                    line=i,
                ))

        # ----------------------------------------------
        # PHP specific checks
        # ----------------------------------------------
        if p.suffix.lower() == ".php":
            for i, line in enumerate(lines, start=1):
                low = line.lower()
                if any(m in low for m in ignore_markers):
                    continue

                for pat in SECRET_PATTERNS:
                    if pat.search(line):
                        severity = "RISK" if mode == SCAN_PROD else "INFO"
                        findings.append(Finding(
                            severity,
                            "Hardcoded secret",
                            line.strip()[:240],
                            str(p),
                            line=i,
                        ))
                        break

                if EMAIL_PATTERN.search(line):
                    if ".env" not in p.name.lower():
                        findings.append(Finding(
                            "INFO",
                            "Hardcoded email",
                            line.strip()[:240],
                            str(p),
                            line=i,
                        ))

                if "display_errors" in low and "ini_set" in low:
                    severity = "RISK" if mode == SCAN_PROD else "INFO"
                    findings.append(Finding(
                        severity,
                        "display_errors enabled",
                        line.strip()[:240],
                        str(p),
                        line=i,
                    ))

                if "error_reporting" in low and "e_all" in low:
                    severity = "RISK" if mode == SCAN_PROD else "INFO"
                    findings.append(Finding(
                        severity,
                        "error_reporting(E_ALL)",
                        line.strip()[:240],
                        str(p),
                        line=i,
                    ))

        # ----------------------------------------------
        # Large file warning
        # ----------------------------------------------
        try:
            size = p.stat().st_size
            if size > 700_000:
                findings.append(Finding(
                    "INFO",
                    "Large file",
                    f"File is {size / 1024:.0f} KB",
                    str(p),
                ))
        except Exception:
            pass

    # --------------------------------------------------
    # Final progress
    # --------------------------------------------------
    if show_progress:
        _emit_progress(100, mode)

    # --------------------------------------------------
    # Sort results
    # --------------------------------------------------
    priority = {"RISK": 0, "TODO": 1, "INFO": 2}
    findings.sort(key=lambda f: (priority.get(f.kind, 9), f.path, f.line or 0))

    return findings
