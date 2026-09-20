import os
import subprocess
import json
import winreg
from datetime import datetime

BACKUP_DIR = os.path.join(os.environ.get("APPDATA", "C:\\"), "WindowsDeepOptimizer", "backups")

def get_backup_dir() -> str:
    """Tạo và trả về thư mục lưu trữ các bản sao lưu Registry."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR

def enable_system_restore_on_c() -> tuple[bool, str]:
    """Bật tính năng System Protection trên ổ đĩa C: nếu chưa bật."""
    try:
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command", "Enable-ComputerRestore -Drive 'C:\\' -ErrorAction Stop"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return True, "Đã bật System Restore trên ổ C: thành công."
        return False, f"Lỗi khi bật System Restore: {res.stderr.strip()}"
    except Exception as e:
        return False, str(e)

def create_system_restore_point(description: str = "Before_Optimization") -> tuple[bool, str]:
    """
    Tạo điểm khôi phục hệ thống (System Restore Point).
    Bỏ qua giới hạn tần suất 24h của Windows để cho phép sao lưu tức thời.
    """
    # Xử lý giới hạn tần suất tạo điểm khôi phục của Windows
    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore") as key:
            winreg.SetValueEx(key, "SystemRestorePointCreationFrequency", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

    # Tạo điểm khôi phục bằng PowerShell
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_desc = f"WDO_{description}_{timestamp}"
    
    ps_cmd = f"Checkpoint-Computer -Description '{full_desc}' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop"
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        if res.returncode == 0:
            return True, f"Tạo điểm khôi phục thành công: {full_desc}"
        else:
            err = res.stderr.strip() or res.stdout.strip()
            # Nếu báo lỗi do ổ đĩa chưa bật System Restore
            if "not enabled" in err.lower() or "chưa bật" in err.lower():
                # Thử tự động bật
                enable_ok, _ = enable_system_restore_on_c()
                if enable_ok:
                    res2 = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if res2.returncode == 0:
                        return True, f"Đã bật System Restore và tạo điểm khôi phục thành công: {full_desc}"
            return False, f"Lỗi tạo Restore Point: {err}"
    except subprocess.TimeoutExpired:
        return False, "Quá thời gian chờ khi tạo Restore Point (Timeout)."
    except Exception as e:
        return False, f"Ngoại lệ khi tạo Restore Point: {e}"

def list_system_restore_points() -> list[dict]:
    """Lấy danh sách các điểm khôi phục hiện có trên máy."""
    ps_cmd = (
        "Get-ComputerRestorePoint -ErrorAction SilentlyContinue | "
        "Select-Object SequenceNumber, Description, CreationTime | "
        "ConvertTo-Json -Depth 2"
    )
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
        return []
    except Exception:
        return []

def backup_registry_key(key_path: str, backup_name: str) -> tuple[bool, str]:
    """
    Xuất file .reg sao lưu nhánh Registry trước khi can thiệp.
    key_path ví dụ: 'HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection'
    """
    try:
        backup_dir = get_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in backup_name if c.isalnum() or c in ('_', '-'))
        filename = f"{safe_name}_{timestamp}.reg"
        filepath = os.path.join(backup_dir, filename)

        cmd = ["reg.exe", "export", key_path, filepath, "/y"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return True, filepath
        else:
            return False, res.stderr.strip()
    except Exception as e:
        return False, str(e)

def restore_registry_from_file(filepath: str) -> tuple[bool, str]:
    """Nhập lại file .reg để khôi phục Registry."""
    if not os.path.exists(filepath):
        return False, f"Tệp sao lưu không tồn tại: {filepath}"
    try:
        cmd = ["reg.exe", "import", filepath]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return True, "Khôi phục Registry từ file thành công."
        else:
            return False, res.stderr.strip()
    except Exception as e:
        return False, str(e)
