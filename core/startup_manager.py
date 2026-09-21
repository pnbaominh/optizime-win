import winreg
from typing import List, Dict, Tuple

STARTUP_KEYS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Người dùng hiện tại (HKCU)"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Toàn hệ thống (HKLM)")
]

def list_startup_items() -> List[Dict[str, str]]:
    """Liệt kê toàn bộ các ứng dụng được cấu hình tự khởi động cùng Windows."""
    items = []
    for root_hkey, sub_key, location_desc in STARTUP_KEYS:
        try:
            with winreg.OpenKey(root_hkey, sub_key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                index = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, index)
                        items.append({
                            "name": name,
                            "command": str(val),
                            "location": location_desc,
                            "root": "HKCU" if root_hkey == winreg.HKEY_CURRENT_USER else "HKLM",
                            "key": sub_key
                        })
                        index += 1
                    except OSError:
                        break
        except Exception:
            continue
    return items

def remove_startup_item(root_str: str, key_path: str, item_name: str) -> Tuple[bool, str]:
    """Gỡ bỏ một ứng dụng khỏi danh sách tự khởi động."""
    root_hkey = winreg.HKEY_CURRENT_USER if root_str == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    try:
        with winreg.OpenKey(root_hkey, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.DeleteValue(key, item_name)
        return True, f"Đã xóa ứng dụng khởi động '{item_name}'."
    except Exception as e:
        return False, f"Không thể xóa '{item_name}': {e}"
