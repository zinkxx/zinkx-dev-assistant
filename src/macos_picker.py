import subprocess


def pick_folder(prompt: str = "Select a folder") -> str | None:
    script = f'''
    tell application "System Events"
      activate
      set theFolder to choose folder with prompt "{prompt}"
      POSIX path of theFolder
    end tell
    '''
    try:
        p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        out = (p.stdout or "").strip()
        if p.returncode != 0 or not out:
            return None
        return out
    except Exception:
        return None
