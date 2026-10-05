import os
import sys
import ctypes
import subprocess
from pathlib import Path

def create_shortcut():
    project_dir = Path(__file__).resolve().parent
    launcher_py = project_dir / "launcher.py"
    icon_path = project_dir / "biomedical_icon.ico"
    
    # Locate pythonw.exe for silent windowless launch
    py_dir = Path(sys.executable).parent
    pythonw_exe = py_dir / "pythonw.exe"
    if not pythonw_exe.exists():
        pythonw_exe = Path(sys.executable)

    # Detect exact Windows Desktop path dynamically
    ps_get_desktop = "[Environment]::GetFolderPath('Desktop')"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_get_desktop],
        capture_output=True, text=True, check=True
    )
    desktop_dir = Path(result.stdout.strip())
    if not desktop_dir.exists():
        desktop_dir = Path(os.path.expanduser("~")) / "Desktop"
        
    shortcut_path = desktop_dir / "LectureAI.lnk"
    
    # Remove old shortcut file if it exists so Windows cache is broken
    if shortcut_path.exists():
        try:
            shortcut_path.unlink()
        except Exception as e:
            print("Notice:", e)

    # Create Windows Shortcut using WScript.Shell via PowerShell
    ps_create_shortcut = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{pythonw_exe}'
$Shortcut.Arguments = '"{launcher_py}"'
$Shortcut.WorkingDirectory = '{project_dir}'
$Shortcut.IconLocation = '{icon_path}, 0'
$Shortcut.Description = 'LectureAI - Biomedical Engineering Study Guide & Exam Prep'
$Shortcut.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_create_shortcut],
        capture_output=True, text=True, check=True
    )

    # Notify Windows Explorer shell to refresh all icons immediately
    try:
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0)
    except Exception as e:
        print("Shell notify error:", e)

    print(f"SUCCESS: Created desktop shortcut at: {shortcut_path}")
    print(f"Target: {pythonw_exe} {launcher_py}")
    print(f"Icon: {icon_path}")
    return shortcut_path

if __name__ == "__main__":
    create_shortcut()
