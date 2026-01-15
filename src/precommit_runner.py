#!/usr/bin/env python3
import sys
import os
from pathlib import Path

from scanner import scan_project, SCAN_PROD
from git_changed import get_changed_files
from report_html import write_html_report


def main() -> int:
    repo_root = Path.cwd()

    changed = get_changed_files(str(repo_root))
    if not changed:
        print("✔ No changed files. Commit allowed.")
        return 0

    findings = scan_project(
        str(repo_root),
        mode=SCAN_PROD,
        only_files=changed,
    )

    risks = [f for f in findings if f.kind == "RISK"]

    report = write_html_report(findings, str(repo_root), out_dir="reports")

    if risks:
        print("\n🚨 COMMIT BLOCKED — Security Risks Found")
        print(f"→ Risks: {len(risks)}")
        print(f"→ Report: {report}\n")
        os.system(f"open '{report}'")
        return 1

    print("✔ Scan clean. Commit allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
