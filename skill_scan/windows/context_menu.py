"""Install / uninstall 'Scan with SkillScan' Windows Explorer context menu entries."""
import sys
import winreg
from pathlib import Path


_MENU_LABEL = "Scan with SkillScan"
_ICON_KEY = "Icon"

# Registry paths for folder right-click and folder-background right-click
_REG_PATHS = [
    r"Software\Classes\Directory\shell\ScanAsAISkill",
    r"Software\Classes\Directory\Background\shell\ScanAsAISkill",
]


def _python_exe() -> str:
    return sys.executable


def _command(path_placeholder: str) -> str:
    exe = _python_exe()
    module = str(Path(__file__).resolve().parents[2] / "skill_scan" / "__main__.py")
    return f'"{exe}" "{module}" --scan "{path_placeholder}"'


def install() -> None:
    python = _python_exe()
    main_py = str(Path(__file__).resolve().parents[2] / "skill_scan" / "__main__.py")

    for reg_path in _REG_PATHS:
        # shell key
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _MENU_LABEL)
        winreg.SetValueEx(key, _ICON_KEY, 0, winreg.REG_SZ, python)
        winreg.CloseKey(key)

        # command subkey
        if "Background" in reg_path:
            placeholder = "%V"
        else:
            placeholder = "%1"
        cmd_key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            reg_path + r"\command",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(
            cmd_key, "", 0, winreg.REG_SZ,
            f'"{python}" "{main_py}" --scan "{placeholder}"'
        )
        winreg.CloseKey(cmd_key)


def uninstall() -> None:
    for reg_path in _REG_PATHS:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path + r"\command")
        except FileNotFoundError:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path)
        except FileNotFoundError:
            pass


def is_installed() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATHS[0])
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
