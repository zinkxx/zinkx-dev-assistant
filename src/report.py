from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from scanner import Finding


def write_report(findings: Iterable[Finding], project_root: str, out_dir: str) -> Path:
    outp = Path(out_dir).expanduser().resolve()
    outp.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_file = outp / f"report-{ts}.md"

    risks = [f for f in findings if f.kind == "RISK"]
    todos = [f for f in findings if f.kind == "TODO"]
    infos = [f for f in findings if f.kind == "INFO"]

    lines: list[str] = []
    lines.append(f"# Zinkx Dev Assistant — Project Scan\n")
    lines.append(f"- **Project:** `{project_root}`")
    lines.append(f"- **Date:** {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"## Summary")
    lines.append(f"- 🚨 Risks: **{len(risks)}**")
    lines.append(f"- 🧩 TODO/FIXME: **{len(todos)}**")
    lines.append(f"- ℹ️ Info: **{len(infos)}**")
    lines.append("")

    def section(title: str, items: list[Finding]):
        lines.append(f"## {title}")
        if not items:
            lines.append("_No items._\n")
            return
        for f in items[:400]:  # çok şişmesin
            lines.append(f"- **[{f.kind}] {f.title}**")
            lines.append(f"  - {f.detail}")
            if f.line:
                vscode_link = f"vscode://file/{f.path}:{f.line}"
                lines.append(f"  - [{f.path}:{f.line}]({vscode_link})")
            else:
                lines.append(f"  - `{f.path}`")
        lines.append("")

    section("🚨 Risks", risks)
    section("🧩 TODO / FIXME", todos)
    section("ℹ️ Info", infos)

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return report_file
