import rumps
from config import load_config, save_config


# --------------------------------------------------
# General Settings
# --------------------------------------------------
def open_general_settings():
    cfg = load_config()

    win = rumps.Window(
        title="General Settings",
        message=(
            "Default Scan Mode (dev / prod):\n"
            "Risk Threshold (0 = any risk triggers alarm):"
        ),
        default_text=(
            f"{cfg.get('default_mode', 'dev')}\n"
            f"{cfg.get('risk_threshold', 0)}"
        ),
        ok="Save",
        cancel="Cancel",
        dimensions=(420, 160),
    )

    resp = win.run()
    if not resp.clicked:
        return

    try:
        lines = resp.text.splitlines()
        mode = lines[0].strip().lower()
        threshold = int(lines[1].strip())

        if mode not in ("dev", "prod"):
            raise ValueError("Mode must be dev or prod")

        cfg["default_mode"] = mode
        cfg["risk_threshold"] = threshold
        save_config(cfg)

        rumps.notification("Zinkx", "General Settings", "Saved successfully")

    except Exception as e:
        rumps.alert("Invalid settings", str(e))


# --------------------------------------------------
# Ignore Rules
# --------------------------------------------------
def open_ignore_settings():
    cfg = load_config()
    markers = "\n".join(cfg.get("ignore_inline_markers", []))

    win = rumps.Window(
        title="Ignore Rules",
        message="Inline ignore markers (one per line):",
        default_text=markers,
        ok="Save",
        cancel="Cancel",
        dimensions=(420, 260),
    )

    resp = win.run()
    if not resp.clicked:
        return

    markers = [l.strip() for l in resp.text.splitlines() if l.strip()]
    cfg["ignore_inline_markers"] = markers
    save_config(cfg)

    rumps.notification("Zinkx", "Ignore Rules", "Updated")


# --------------------------------------------------
# Settings Root
# --------------------------------------------------
def open_settings_root():
    # sadece bilgi amaçlı; menüden açılıyor
    rumps.alert(
        "Settings",
        "Choose a category from the menu:\n\n"
        "• General\n"
        "• Ignore Rules"
    )
