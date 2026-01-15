import json
import os
from typing import Dict, Any

# --------------------------------------------------
# Config path
# --------------------------------------------------
CONFIG_PATH = os.path.expanduser("~/.zinkx_dev_assistant/config.json")

# --------------------------------------------------
# Default config (single source of truth)
# --------------------------------------------------
DEFAULT_CONFIG: Dict[str, Any] = {

    # =========================
    # Scan behavior
    # =========================
    "default_mode": "dev",            # dev | prod
    "risk_threshold": 0,              # kaç risk olunca alarm

    # Progress / IPC
    "show_scan_progress": True,       # scan sırasında progress bar göster
    "scan_progress_steps": [20, 50, 80, 100],  # IPC % adımları

    # =========================
    # Ignore rules
    # =========================
    "ignore_env": True,               # .env dosyalarını yok say
    "ignore_node_modules": True,      # node_modules yok say
    "ignore_inline_markers": [
        "zinkx-ignore",
        "ignore-security",
        "safe",
    ],

    # =========================
    # Reports / UX
    # =========================
    "reports": {
        "max_recent": 20,             # recent reports limiti
        "default_severity_filter": {  # reports ekranı default filtre
            "RISK": True,
            "TODO": True,
        },
        "enable_search": True,        # report search aktif
        "inline_preview": False,      # (ileride) HTML inline preview
    },

    # =========================
    # UI / Theme
    # =========================
    "theme": "dark",                  # dark | light | system
    "remember_last_page": True,       # app açıldığında son sayfa
}

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def _merge_with_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Eksik alanları DEFAULT_CONFIG ile tamamlar.
    Nested dict'leri de güvenli şekilde merge eder.
    """
    merged = DEFAULT_CONFIG.copy()

    for key, value in (cfg or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    return merged

# --------------------------------------------------
# Load config
# --------------------------------------------------
def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        cfg = DEFAULT_CONFIG.copy()
        save_config(cfg)
        return cfg

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)

        cfg = _merge_with_defaults(raw)
        save_config(cfg)  # eksik alanları kalıcı yaz (auto-migrate)
        return cfg

    except Exception:
        cfg = DEFAULT_CONFIG.copy()
        save_config(cfg)
        return cfg

# --------------------------------------------------
# Save config
# --------------------------------------------------
def save_config(cfg: Dict[str, Any]):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    # Partial update’ler için güvenli merge
    final_cfg = _merge_with_defaults(cfg)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(final_cfg, f, indent=2, ensure_ascii=False)
