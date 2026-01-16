import sys
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem,
    QStackedWidget, QProgressBar, QCheckBox,
    QComboBox, QSlider, QFormLayout
)
from PySide6.QtCore import Qt, QTimer, QUrl, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QScrollArea

import qtawesome as qta
from qt_material import apply_stylesheet

from ipc import send_command, read_status, read_command, clear_command
from config import load_config, save_config


# ==================================================
# Theme helper
# ==================================================
def apply_theme(app, theme: str):
    if theme == "light":
        apply_stylesheet(app, theme="light_blue.xml")
    else:
        apply_stylesheet(app, theme="dark_teal.xml")


# ==================================================
# Main Window
# ==================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --------------------------------------------------
        # Config
        # --------------------------------------------------
        self.cfg = load_config()

        # --------------------------------------------------
        # Window
        # --------------------------------------------------
        self.setWindowTitle("Zinkx Dev Assistant")
        self.setMinimumSize(1050, 650)

        base_dir = os.path.dirname(__file__)
        self.reports_dir = os.path.join(base_dir, "..", "reports")

        icon_path = os.path.join(base_dir, "..", "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))


        # --------------------------------------------------
        # State
        # --------------------------------------------------
        self.project_path = None
        self._last_status_hash = None

        # --------------------------------------------------
        # Root
        # --------------------------------------------------
        root = QWidget(self)
        root.setObjectName("appRoot")  # tema / stylesheet için hook
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)      # sidebar + content arası net çizgi


        # ==================================================
        # Sidebar
        # ==================================================
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QWidget {
                background:#0f172a;
                color:#e5e7eb;
            }
        """)

        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(20, 26, 20, 20)
        sb.setSpacing(10)

        # --------------------------------------------------
        # Brand / Header
        # --------------------------------------------------
        brand = QLabel("<h2 style='margin:0'>Zinkx</h2>")
        subtitle = QLabel("Dev Assistant")
        subtitle.setStyleSheet("color:#94a3b8;font-size:12px;")

        sb.addWidget(brand)
        sb.addWidget(subtitle)
        sb.addSpacing(28)

        # --------------------------------------------------
        # Navigation button factory
        # --------------------------------------------------
        def nav(text, icon):
            b = QPushButton(text)
            b.setIcon(qta.icon(icon, color="#e5e7eb"))
            b.setIconSize(QSize(18, 18))
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(48)
            b.setStyleSheet("""
                QPushButton {
                    text-align:left;
                    padding:12px 14px;
                    border-radius:12px;
                    font-weight:500;
                }
                QPushButton:hover {
                    background:rgba(255,255,255,0.10);
                }
                QPushButton:checked {
                    background: linear-gradient(
                        90deg,
                        rgba(59,130,246,0.35),
                        rgba(59,130,246,0.15)
                    );
                    border-left: 4px solid #3b82f6;
                    color: #ffffff;
                }
            """)
            return b

        # --------------------------------------------------
        # Nav buttons
        # --------------------------------------------------
        self.btn_dashboard = nav("Dashboard", "mdi.view-dashboard-outline")
        self.btn_scan = nav("Scan", "mdi.magnify")
        self.btn_reports = nav("Reports", "mdi.file-document-outline")
        self.btn_settings = nav("Settings", "mdi.cog-outline")

        self.navs = [
            self.btn_dashboard,
            self.btn_scan,
            self.btn_reports,
            self.btn_settings,
        ]

        self.btn_dashboard.setChecked(True)

        for b in self.navs:
            sb.addWidget(b)

        sb.addStretch()

        # --------------------------------------------------
        # Sidebar footer (App info)
        # --------------------------------------------------
        status_chip = QLabel("● Idle")
        status_chip.setStyleSheet("""
            QLabel {
                color:#22c55e;
                font-size:11px;
                padding:6px 10px;
                border-radius:999px;
                background:rgba(34,197,94,0.15);
            }
        """)
        sb.addWidget(status_chip)

        footer = QLabel(
            "<div style='line-height:1.4'>"
            "<b>Zinkx Dev Assistant</b><br>"
            "<span style='color:#94a3b8;font-size:11px'>v0.9.0 · Security Scanner</span>"
            "</div>"
        )
        footer.setStyleSheet("margin-top:8px;")
        sb.addWidget(footer)

        root_layout.addWidget(sidebar)


        # ==================================================
        # Pages
        # ==================================================
        self.pages = QStackedWidget()
        root_layout.addWidget(self.pages)

        self.page_dashboard = QWidget()
        self.page_scan = QWidget()
        self.page_reports = QWidget()
        self.page_settings = QWidget()

        self.pages.addWidget(self.page_dashboard)
        self.pages.addWidget(self.page_scan)
        self.pages.addWidget(self.page_reports)
        self.pages.addWidget(self.page_settings)

        self.build_dashboard()
        self.build_scan()
        self.build_reports()
        self.build_settings()

        for i, b in enumerate(self.navs):
            b.clicked.connect(lambda _, x=i: self.switch_page(x))

        # --------------------------------------------------
        # IPC Timers
        # --------------------------------------------------
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.poll_status)
        self.status_timer.start(500)

        self.cmd_timer = QTimer(self)
        self.cmd_timer.timeout.connect(self.poll_commands)
        self.cmd_timer.start(500)

        self.load_reports()

    # ==================================================
    # Pages
    # ==================================================
    def build_dashboard(self):
        # ==================================================
        # Root layout (dashboard)
        # ==================================================
        page_layout = QVBoxLayout(self.page_dashboard)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea(self.page_dashboard)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        page_layout.addWidget(scroll)

        content = QWidget(scroll)
        scroll.setWidget(content)

        l = QVBoxLayout(content)
        l.setContentsMargins(32, 32, 32, 32)
        l.setSpacing(20)


        # --------------------------------------------------
        # Header
        # --------------------------------------------------
        l.addWidget(QLabel("<h1>Dashboard</h1>"))

        subtitle = QLabel("Overview of last scan & project status")
        subtitle.setStyleSheet("color:#9ca3af;")
        l.addWidget(subtitle)

        # --------------------------------------------------
        # Stat cards
        # --------------------------------------------------
        cards = QHBoxLayout()
        cards.setSpacing(16)

        def card(title, icon, subtitle):
            w = QWidget()
            w.setStyleSheet("""
                QWidget {
                    background: rgba(255,255,255,0.06);
                    border-radius: 16px;
                    padding: 18px;
                }
            """)
            lay = QVBoxLayout(w)
            lay.setSpacing(4)

            top = QHBoxLayout()
            top.addWidget(QLabel(f"<b>{title}</b>"))
            top.addStretch()
            top.addWidget(QLabel(icon))
            lay.addLayout(top)

            value = QLabel("0")
            value.setStyleSheet("font-size:32px;font-weight:700;")
            lay.addWidget(value)

            hint = QLabel(subtitle)
            hint.setStyleSheet("color:#9ca3af;font-size:11px;")
            lay.addWidget(hint)

            return w, value


        card_risk, self.lbl_risk = card("Risks", "⚠️", "Potential security issues")
        card_todo, self.lbl_todo = card("TODOs", "📝", "Code comments & notes")


        cards.addWidget(card_risk)
        cards.addWidget(card_todo)
        cards.addStretch()

        l.addLayout(cards)

        # --------------------------------------------------
        # Project info panel
        # --------------------------------------------------
        project_box = QWidget()
        project_box.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.04);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        pb = QVBoxLayout(project_box)
        pb.setSpacing(6)

        pb.addWidget(QLabel("<b>Last Project</b>"))

        self.lbl_project = QLabel("No project selected")
        self.lbl_project.setStyleSheet("color:#9ca3af;")
        pb.addWidget(self.lbl_project)

        l.addWidget(project_box)

        # --------------------------------------------------
        # Last scan summary
        # --------------------------------------------------
        summary = QWidget()
        summary.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.03);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        sl = QVBoxLayout(summary)
        sl.setSpacing(6)

        sl.addWidget(QLabel("<b>Last Scan Summary</b>"))

        self.lbl_dash = QLabel("No scan performed yet.")
        self.lbl_dash.setStyleSheet("color:#9ca3af;")
        sl.addWidget(self.lbl_dash)

        l.addWidget(summary)

        # --------------------------------------------------
        # Hint / help text
        # --------------------------------------------------
        hint = QLabel(
            "• Use the Scan tab to analyze your project\n"
            "• Dev mode shows INFO, Prod mode focuses on RISK\n"
            "• Reports are generated after each scan"
        )
        hint.setStyleSheet("color:#6b7280;")
        l.addWidget(hint)

        l.addStretch()


    def build_scan(self):
        l = QVBoxLayout(self.page_scan)
        l.setContentsMargins(32, 32, 32, 32)
        l.setSpacing(20)

        # --------------------------------------------------
        # Header
        # --------------------------------------------------
        l.addWidget(QLabel("<h1>Scan Project</h1>"))

        subtitle = QLabel("Select a project folder and start scanning")
        subtitle.setStyleSheet("color:#9ca3af;")
        l.addWidget(subtitle)

        # --------------------------------------------------
        # Action buttons (cards style)
        # --------------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(16)

        def scan_card(title, desc, icon_path, bg, fg):
            w = QWidget()
            w.setCursor(Qt.PointingHandCursor)
            w.setStyleSheet(f"""
                QWidget {{
                    background:{bg};
                    border-radius:16px;
                    padding:18px;
                }}
                QWidget:hover {{
                    background:rgba(255,255,255,0.10);
                }}
            """)

            lay = QVBoxLayout(w)
            lay.setSpacing(8)

            icon = QLabel()
            icon.setPixmap(QIcon(icon_path).pixmap(28, 28))
            lay.addWidget(icon)

            lay.addWidget(QLabel(f"<b>{title}</b>"))

            d = QLabel(desc)
            d.setStyleSheet("color:#9ca3af; font-size:12px;")
            lay.addWidget(d)

            return w

        base_dir = os.path.dirname(__file__)
        icon_dir = os.path.join(base_dir, "..", "assets", "icons")

        self.card_choose = scan_card(
            "Choose Project",
            "Select root folder",
            os.path.join(icon_dir, "folder.svg"),
            "rgba(255,255,255,0.05)",
            "#fff"
        )

        self.card_dev = scan_card(
            "Scan (Dev)",
            "Development scan",
            os.path.join(icon_dir, "play-dev.svg"),
            "rgba(37,99,235,0.25)",
            "#fff"
        )

        self.card_prod = scan_card(
            "Scan (Prod)",
            "Strict production scan",
            os.path.join(icon_dir, "alert-prod.svg"),
            "rgba(185,28,28,0.25)",
            "#fff"
        )

        actions.addWidget(self.card_choose)
        actions.addWidget(self.card_dev)
        actions.addWidget(self.card_prod)
        actions.addStretch()

        l.addLayout(actions)

        # --------------------------------------------------
        # Status & Progress
        # --------------------------------------------------
        self.scan_status = QLabel("No project selected.")
        self.scan_status.setStyleSheet("color:#9ca3af;")
        l.addWidget(self.scan_status)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
        QProgressBar {
            background: rgba(255,255,255,0.08);
            border-radius: 3px;
        }
        QProgressBar::chunk {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #3b82f6,
                stop:1 #22d3ee
            );
            border-radius: 3px;
        }
        """)
        self.progress.hide()
        l.addWidget(self.progress)

        # --------------------------------------------------
        # Click bindings
        # --------------------------------------------------
        self.card_choose.mousePressEvent = lambda e: self.choose_project()
        self.card_dev.mousePressEvent = lambda e: self.start_scan("dev")
        self.card_prod.mousePressEvent = lambda e: self.start_scan("prod")

        l.addStretch()


    def build_reports(self):
        wrapper = QHBoxLayout(self.page_reports)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)

        # ==================================================
        # LEFT – Report List (Enhanced)
        # ==================================================
        left = QWidget()
        left.setFixedWidth(360)
        left.setStyleSheet("""
            QWidget {
                background:#020617;
                border-right:1px solid rgba(255,255,255,0.06);
            }
        """)

        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 20, 16, 16)
        ll.setSpacing(12)

        title = QLabel("<h2>Reports</h2>")
        subtitle = QLabel("Latest scan results")
        subtitle.setStyleSheet("color:#94a3b8;font-size:12px;")

        ll.addWidget(title)
        ll.addWidget(subtitle)

        self.reports_list = QListWidget()
        self.reports_list.setSpacing(8)
        self.reports_list.setStyleSheet("""
            QListWidget {
                background:transparent;
                border:none;
            }
            QListWidget::item {
                background:rgba(255,255,255,0.04);
                border-radius:12px;
                padding:12px;
            }
            QListWidget::item:selected {
                background:rgba(59,130,246,0.25);
            }
        """)
        self.reports_list.itemClicked.connect(self.open_report)

        ll.addWidget(self.reports_list)
        wrapper.addWidget(left)

        # ==================================================
        # RIGHT – Report Viewer
        # ==================================================
        self.report_view = QWebEngineView()
        self.report_view.setStyleSheet("background:#020617;")

        wrapper.addWidget(self.report_view)

    def build_settings(self):
        # --- page_settings sadece scroll taşır
        page_layout = QVBoxLayout(self.page_settings)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        page_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(28)

        # ---------------- Header ----------------
        content_layout.addWidget(QLabel("<h1>Settings</h1>"))

        subtitle = QLabel("Customize scanning behavior & application preferences")
        subtitle.setStyleSheet("color:#9ca3af;")
        content_layout.addWidget(subtitle)

        # ---------------- Card helper ----------------
        def card(title):
            w = QWidget()
            w.setStyleSheet("""
                QWidget {
                    background: rgba(255,255,255,0.04);
                    border-radius: 16px;
                }
            """)
            v = QVBoxLayout(w)
            v.setContentsMargins(20, 20, 20, 20)
            v.setSpacing(14)
            v.addWidget(QLabel(f"<b>{title}</b>"))
            return w, v

        # ---------------- Appearance ----------------
        appearance, al = card("Appearance")

        row = QHBoxLayout()
        row.addWidget(QLabel("Theme"))
        row.addStretch()

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["dark", "light", "system"])
        self.cmb_theme.setCurrentText(self.cfg.get("theme", "dark"))
        self.cmb_theme.setMinimumWidth(180)
        row.addWidget(self.cmb_theme)

        al.addLayout(row)

        desc = QLabel("Change application theme (restart not required)")
        desc.setStyleSheet("color:#94a3b8;font-size:12px;")
        al.addWidget(desc)

        content_layout.addWidget(appearance)

        # ---------------- Scan Defaults ----------------
        scan, sl = card("Scan Defaults")

        row = QHBoxLayout()
        row.addWidget(QLabel("Default Scan Mode"))
        row.addStretch()

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["dev", "prod"])
        self.cmb_mode.setCurrentText(self.cfg.get("default_mode", "dev"))
        self.cmb_mode.setMinimumWidth(180)
        row.addWidget(self.cmb_mode)

        sl.addLayout(row)

        sl.addWidget(QLabel("Risk Threshold"))

        self.slider_risk = QSlider(Qt.Horizontal)
        self.slider_risk.setRange(0, 10)
        self.slider_risk.setValue(self.cfg.get("risk_threshold", 0))
        self.slider_risk.setFixedHeight(22)
        sl.addWidget(self.slider_risk)

        risk_desc = QLabel("Minimum risk count to highlight warnings")
        risk_desc.setStyleSheet("color:#94a3b8;font-size:12px;")
        sl.addWidget(risk_desc)

        content_layout.addWidget(scan)

        # ---------------- Ignore Rules ----------------
        ignore, il = card("Ignore Rules")

        self.chk_env = QCheckBox("Ignore .env files")
        self.chk_node = QCheckBox("Ignore node_modules directory")

        self.chk_env.setChecked(self.cfg.get("ignore_env", True))
        self.chk_node.setChecked(self.cfg.get("ignore_node_modules", True))

        il.addWidget(self.chk_env)
        il.addWidget(self.chk_node)

        ignore_desc = QLabel("Ignored files and folders will be skipped during scan.")
        ignore_desc.setStyleSheet("color:#94a3b8;font-size:12px;")
        il.addWidget(ignore_desc)

        content_layout.addWidget(ignore)

        # ---------------- Application Info ----------------
        info, inf = card("Application")
        inf.addWidget(QLabel(
            "<span style='color:#94a3b8;font-size:12px'>"
            "Zinkx Dev Assistant v0.9.0<br>"
            "Local static code & security analyzer"
            "</span>"
        ))

        content_layout.addWidget(info)
        content_layout.addStretch()

        # ---------------- Bindings ----------------
        self.cmb_theme.currentTextChanged.connect(self.save_settings)
        self.cmb_mode.currentTextChanged.connect(self.save_settings)
        self.slider_risk.valueChanged.connect(self.save_settings)
        self.chk_env.stateChanged.connect(self.save_settings)
        self.chk_node.stateChanged.connect(self.save_settings)



    # ==================================================
    # Actions
    # ==================================================
    def switch_page(self, index):
        for b in self.navs:
            b.setChecked(False)
        self.navs[index].setChecked(True)
        self.pages.setCurrentIndex(index)

    def choose_project(self):
        p = QFileDialog.getExistingDirectory(self, "Choose Project")
        if p:
            self.project_path = p
            self.scan_status.setText(p)

    def start_scan(self, mode):
        if not self.project_path:
            self.scan_status.setText("Choose a project first.")
            return

        self.progress.show()
        self.progress.setValue(10)
        self.scan_status.setText("Scanning…")

        send_command({
            "action": "scan",
            "mode": mode,
            "project": self.project_path,
        })

    def save_settings(self):
        self.cfg.update({
            "default_mode": self.cmb_mode.currentText(),
            "risk_threshold": self.slider_risk.value(),
            "ignore_env": self.chk_env.isChecked(),
            "ignore_node_modules": self.chk_node.isChecked(),
            "theme": self.cmb_theme.currentText(),
        })
        save_config(self.cfg)
        apply_theme(QApplication.instance(), self.cfg["theme"])

    # ==================================================
    # Reports
    # ==================================================
    def load_reports(self):
        self.reports_list.clear()

        if not os.path.isdir(self.reports_dir):
            return

        base_dir = os.path.dirname(__file__)
        icon_dir = os.path.join(base_dir, "..", "assets", "icons")

        for f in sorted(os.listdir(self.reports_dir), reverse=True):
            if not f.endswith(".html"):
                continue

            # filename örnek: 2026-01-15_myproject_prod.html
            parts = f.replace(".html", "").split("_")

            date = parts[0] if len(parts) > 0 else "Unknown date"
            project = parts[1] if len(parts) > 1 else "Unknown project"
            mode = parts[2].upper() if len(parts) > 2 else "SCAN"

            item = QListWidgetItem()
            item.setSizeHint(QSize(320, 74))
            item.setData(Qt.UserRole, f)

            widget = QWidget()
            v = QVBoxLayout(widget)
            v.setContentsMargins(8, 6, 8, 6)
            v.setSpacing(4)

            # ---- Title row
            t = QHBoxLayout()
            icon = QLabel()
            icon.setPixmap(QIcon(os.path.join(icon_dir, "report.svg")).pixmap(18, 18))
            t.addWidget(icon)

            t.addWidget(QLabel(f"<b>{project}</b>"))
            t.addStretch()
            t.addWidget(QLabel(f"<span style='color:#60a5fa'>{mode}</span>"))
            v.addLayout(t)

            # ---- Meta row
            meta = QHBoxLayout()

            clock = QLabel()
            clock.setPixmap(QIcon(os.path.join(icon_dir, "clock.svg")).pixmap(14, 14))
            meta.addWidget(clock)
            meta.addWidget(QLabel(f"<span style='color:#94a3b8;font-size:11px'>{date}</span>"))

            meta.addSpacing(10)

            folder = QLabel()
            folder.setPixmap(QIcon(os.path.join(icon_dir, "folder.svg")).pixmap(14, 14))
            meta.addWidget(folder)
            meta.addWidget(QLabel("<span style='color:#94a3b8;font-size:11px'>Project root</span>"))

            meta.addStretch()
            v.addLayout(meta)

            self.reports_list.addItem(item)
            self.reports_list.setItemWidget(item, widget)


    def open_report(self, item):
        filename = item.data(Qt.UserRole)
        path = os.path.join(self.reports_dir, filename)
        self.report_view.setUrl(QUrl.fromLocalFile(path))


    # ==================================================
    # IPC
    # ==================================================
    def poll_status(self):
        st = read_status()
        if not st:
            return

        # Progress update
        if st.get("type") == "progress":
            self.progress.show()
            self.progress.setValue(st.get("percent", 0))
            return

        key = f"{st.get('last_risks')}|{st.get('last_todos')}|{st.get('mode')}"
        if key == self._last_status_hash:
            return

        self._last_status_hash = key
        self.progress.setValue(100)

        self.lbl_risk.setText(str(st["last_risks"]))
        self.lbl_todo.setText(str(st["last_todos"]))

        self.lbl_dash.setText(
            f"✔ Last scan ({st['mode'].upper()}) completed"
        )

        self.scan_status.setText("Scan completed.")
        self.load_reports()

    def poll_commands(self):
        cmd = read_command()
        if cmd and cmd.get("action") == "show_window":
            clear_command()
            self.show()
            self.raise_()
            self.activateWindow()


# ==================================================
# Entrypoint
# ==================================================
def run_main_window():
    app = QApplication(sys.argv)
    cfg = load_config()
    apply_theme(app, cfg.get("theme", "dark"))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())

    app.setStyleSheet("""
    QComboBox {
        padding: 8px 12px;
        min-height: 36px;
        border-radius: 10px;
    }

    QSlider::groove:horizontal {
        height: 6px;
        border-radius: 3px;
    }

    QSlider::handle:horizontal {
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }
    """)


if __name__ == "__main__":
    run_main_window()
