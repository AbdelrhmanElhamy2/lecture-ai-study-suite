import os
import sys
import time
import urllib.request
import urllib.error
import subprocess
import webbrowser
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8000"
CONFIG_URL = f"{URL}/api/config"

def is_server_running() -> bool:
    try:
        req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "LectureAI-Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def start_server():
    if is_server_running():
        return

    # Use python.exe (not pythonw.exe) to run uvicorn cleanly in background
    py_exe = Path(sys.executable)
    if py_exe.name.lower() == "pythonw.exe":
        normal_py = py_exe.parent / "python.exe"
        if normal_py.exists():
            py_exe = normal_py

    cmd = [
        str(py_exe),
        "-m", "uvicorn",
        "app:app",
        "--host", "127.0.0.1",
        "--port", "8000"
    ]

    # Flags to suppress console window on Windows
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creation_flags |= subprocess.DETACHED_PROCESS

    subprocess.Popen(
        cmd,
        cwd=str(PROJECT_DIR),
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )

    # Wait for server to become responsive
    for _ in range(25):
        time.sleep(0.3)
        if is_server_running():
            break

def find_app_browser() -> str:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return ""

def open_app_window():
    browser_exe = find_app_browser()
    if browser_exe:
        # Launch standalone frameless app window
        try:
            subprocess.Popen([browser_exe, f"--app={URL}"])
            return
        except Exception:
            pass

    # Fallback to default web browser
    webbrowser.open(URL)

def main():
    start_server()
    open_app_window()

if __name__ == "__main__":
    main()
