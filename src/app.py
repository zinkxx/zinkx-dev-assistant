import os
import subprocess
import rumps

from macos_picker import pick_folder
from scanner import scan_project, SCAN_DEV, SCAN_PROD
from report_html import write_html_report
from install_hook import install_precommit_hook
from settings_ui import (
    open_general_settings,
    open_ignore_settings,
)
from config import load_config
from ipc import (
    read_command,
    clear_command,
    write_status,
    send_command,   # 👈 EKLENDİ
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def open_path(path: str):
    try:
        subprocess.run(["open", path], check=False)
    except Exception as e:
        rumps.alert("Open failed", str(e))


# --------------------------------------------------
# App (Menu Bar)
# --------------------------------------------------
class ZinkxDevAssistant(rumps.App):
    def __init__(self):
        super().__init__("Zinkx", icon="assets/icon.png", quit_button=None)

        # macOS hybrid app uyumu
        self.application_supports_secure_restorable_state = True

        # --------------------------------------------------
        # State
        # --------------------------------------------------
        self.state_dir = os.path.expanduser("~/.zinkx_dev_assistant")
        os.makedirs(self.state_dir, exist_ok=True)

        self.project_path_file = os.path.join(self.state_dir, "last_project.txt")
        self.last_report_file = os.path.join(self.state_dir, "last_report.txt")

        self.project_root = self._load_last_project()

        # Scan summary (badge için)
        self.last_risks = 0
        self.last_todos = 0

        # --------------------------------------------------
        # Settings submenu
        # --------------------------------------------------
        settings_menu = rumps.MenuItem("Settings")
        settings_menu.add(
            rumps.MenuItem("General…", callback=self.open_general_settings)
        )
        settings_menu.add(
            rumps.MenuItem("Ignore Rules…", callback=self.open_ignore_settings)
        )

        # --------------------------------------------------
        # Menu
        # --------------------------------------------------
        self.menu = [
            # 👇 YENİ
            rumps.MenuItem("Show Main Window", callback=self.show_main_window),
            None,

            rumps.MenuItem("Choose Project Folder…", callback=self.choose_project),
            rumps.MenuItem("Scan (Default Mode)", callback=self.scan_default),
            rumps.MenuItem("Scan (Dev Mode)", callback=self.scan_dev),
            rumps.MenuItem("Scan (Prod Mode)", callback=self.scan_prod),
            rumps.MenuItem("Open Last Report", callback=self.open_last_report),
            None,
            settings_menu,
            rumps.MenuItem("Install Git Pre-commit Hook", callback=self.install_hook),
            rumps.MenuItem("Quick Note", callback=self.quick_note),
            None,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        # Initial UI state
        self._update_title_badge()
        self._refresh_mode_checks()

        # --------------------------------------------------
        # IPC command listener (Qt → Menu Bar)
        # --------------------------------------------------
        self._cmd_timer = rumps.Timer(self._poll_commands, 1)
        self._cmd_timer.start()

    # --------------------------------------------------
    # IPC
    # --------------------------------------------------
    def _poll_commands(self, _):
        cmd = read_command()
        if not cmd:
            return

        clear_command()

        action = cmd.get("action")
        mode = cmd.get("mode")
        project = cmd.get("project")

        if action == "scan" and project:
            self.project_root = project
            self._save_last_project(project)

            self._scan_with_mode(
                SCAN_PROD if mode == "prod" else SCAN_DEV
            )

            write_status({
                "last_risks": self.last_risks,
                "last_todos": self.last_todos,
                "mode": mode,
            })

    # --------------------------------------------------
    # Menu → Qt
    # --------------------------------------------------
    def show_main_window(self, _):
        send_command({
            "action": "show_window"
        })

    # --------------------------------------------------
    # Badge / Menu State
    # --------------------------------------------------
    def _update_title_badge(self):
        cfg = load_config()
        threshold = int(cfg.get("risk_threshold", 0))

        if self.last_risks > threshold:
            self.title = f"Zinkx 🚨{self.last_risks}"
        elif self.last_todos > 0:
            self.title = f"Zinkx ⚠︎{self.last_todos}"
        else:
            self.title = "Zinkx ✔"

    def _refresh_mode_checks(self):
        cfg = load_config()
        mode = cfg.get("default_mode", "dev")

        self.menu["Scan (Dev Mode)"].state = 0
        self.menu["Scan (Prod Mode)"].state = 0

        if mode == "prod":
            self.menu["Scan (Prod Mode)"].state = 1
        else:
            self.menu["Scan (Dev Mode)"].state = 1

    # --------------------------------------------------
    # State helpers
    # --------------------------------------------------
    def _load_last_project(self) -> str | None:
        try:
            if os.path.exists(self.project_path_file):
                p = open(self.project_path_file, "r", encoding="utf-8").read().strip()
                return p if p else None
        except Exception:
            pass
        return None

    def _save_last_project(self, path: str):
        with open(self.project_path_file, "w", encoding="utf-8") as f:
            f.write(path)

    def _save_last_report(self, path: str):
        with open(self.last_report_file, "w", encoding="utf-8") as f:
            f.write(path)

    def _load_last_report(self) -> str | None:
        try:
            if os.path.exists(self.last_report_file):
                p = open(self.last_report_file, "r", encoding="utf-8").read().strip()
                return p if p else None
        except Exception:
            pass
        return None

    # --------------------------------------------------
    # Menu actions
    # --------------------------------------------------
    def choose_project(self, _):
        chosen = pick_folder("Choose a project folder to scan")
        if not chosen:
            return

        self.project_root = chosen
        self._save_last_project(chosen)
        rumps.notification("Zinkx", "Project Selected", chosen)

    def scan_default(self, _):
        cfg = load_config()
        mode = cfg.get("default_mode", "dev")
        self._scan_with_mode(SCAN_PROD if mode == "prod" else SCAN_DEV)

    def scan_dev(self, _):
        self._scan_with_mode(SCAN_DEV)

    def scan_prod(self, _):
        self._scan_with_mode(SCAN_PROD)

    # --------------------------------------------------
    # Core scan
    # --------------------------------------------------
    def _scan_with_mode(self, mode: str):
        if not self.project_root or not os.path.isdir(self.project_root):
            rumps.alert("No project selected", "Choose Project Folder first.")
            return

        findings = scan_project(self.project_root, mode=mode)
        report_path = write_html_report(
            findings,
            self.project_root,
            out_dir="reports",
        )
        self._save_last_report(str(report_path))

        risks = sum(1 for f in findings if f.kind == "RISK")
        todos = sum(1 for f in findings if f.kind == "TODO")

        self.last_risks = risks
        self.last_todos = todos
        self._update_title_badge()
        self._refresh_mode_checks()

        label = "PROD" if mode == SCAN_PROD else "DEV"

        rumps.notification(
            "Zinkx",
            f"Scan Complete ({label})",
            f"Risks: {risks} | TODO: {todos}",
        )

        open_path(str(report_path))

    # --------------------------------------------------
    # Other actions
    # --------------------------------------------------
    def open_last_report(self, _):
        p = self._load_last_report()
        if not p or not os.path.exists(p):
            rumps.alert("No report yet", "Run a scan first.")
            return
        open_path(p)

    def open_general_settings(self, _):
        open_general_settings()
        self._update_title_badge()
        self._refresh_mode_checks()

    def open_ignore_settings(self, _):
        open_ignore_settings()

    def install_hook(self, _):
        if not self.project_root or not os.path.isdir(self.project_root):
            rumps.alert("No project selected", "Choose Project Folder first.")
            return

        try:
            hook = install_precommit_hook(self.project_root)
            rumps.notification(
                "Zinkx",
                "Pre-commit Hook Installed",
                str(hook),
            )
        except Exception as e:
            rumps.alert("Hook install failed", str(e))

    def quick_note(self, _):
        win = rumps.Window(
            title="Quick Note",
            message="Notunu yaz (kaydedilecek):",
            default_text="",
            ok="Save",
            cancel="Cancel",
        )
        resp = win.run()
        if not resp.clicked:
            return

        note = resp.text.strip()
        if not note:
            return

        notes_file = os.path.join(self.state_dir, "notes.txt")
        with open(notes_file, "a", encoding="utf-8") as f:
            f.write(note + "\n")

        rumps.notification("Zinkx", "Saved", "Not kaydedildi ✅")


# --------------------------------------------------
# Entrypoint
# --------------------------------------------------
if __name__ == "__main__":
    ZinkxDevAssistant().run()
