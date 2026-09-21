import sys
import os
import ctypes
import platform
import shutil
from core.process_utils import run_cmd

def is_admin() -> bool:
    """Kiểm tra ứng dụng có đang chạy với quyền Administrator hay không."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_if_not_admin() -> bool:
    """Nếu chưa có quyền Admin, tự động gọi UAC để yêu cầu quyền và khởi động lại."""
    if is_admin():
        return True
    
    try:
        # Lấy đường dẫn file thực thi và arguments
        if getattr(sys, 'frozen', False):
            # Chạy từ file exe (PyInstaller)
            executable = sys.executable
            args = ""
        else:
            # Chạy từ source python - dùng pythonw.exe để không hiện CMD nếu có
            py_dir = os.path.dirname(sys.executable)
            pythonw = os.path.join(py_dir, "pythonw.exe")
            executable = pythonw if os.path.exists(pythonw) else sys.executable
            args = f'"{os.path.abspath(sys.argv[0])}"'
            if len(sys.argv) > 1:
                args += " " + " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # Gọi ShellExecuteW với động từ 'runas' để kích hoạt UAC
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            args,
            None,
            1  # SW_SHOWNORMAL
        )
        if ret > 32:
            sys.exit(0)
            return True
        return False
    except Exception as e:
        print(f"Lỗi khi yêu cầu quyền Admin: {e}")
        return False

def get_windows_version_info() -> dict:
    """Lấy thông tin chi tiết phiên bản Windows và build number."""
    win_ver = sys.getwindowsversion()
    build = win_ver.build
    major = win_ver.major
    minor = win_ver.minor

    # Windows 11 bắt đầu từ build 22000
    if build >= 22000:
        os_name = "Windows 11"
        if build >= 26100:
            version_tag = "24H2"
        elif build >= 22631:
            version_tag = "23H2"
        elif build >= 22621:
            version_tag = "22H2"
        else:
            version_tag = "21H2"
    else:
        os_name = "Windows 10"
        if build >= 19045:
            version_tag = "22H2"
        elif build >= 19044:
            version_tag = "21H2"
        else:
            version_tag = f"Build {build}"

    return {
        "os_name": os_name,
        "version_tag": version_tag,
        "build_number": build,
        "full_name": f"{os_name} ({version_tag} - Build {build})",
        "architecture": platform.machine(),
        "is_admin": is_admin()
    }

def get_system_storage_stats() -> dict:
    """Lấy dung lượng ổ đĩa hệ thống C:"""
    try:
        total, used, free = shutil.disk_usage("C:\\")
        gb = 1024 ** 3
        return {
            "total_gb": round(total / gb, 1),
            "used_gb": round(used / gb, 1),
            "free_gb": round(free / gb, 1),
            "free_percent": round((free / total) * 100, 1)
        }
    except Exception:
        return {
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "free_percent": 0
        }

def is_system_restore_enabled() -> bool:
    """Kiểm tra xem System Restore trên ổ C: có đang được bật hay không."""
    try:
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command", "Get-ComputerRestorePoint -ErrorAction SilentlyContinue"
        ]
        res = run_cmd(cmd, timeout=5)
        # Nếu lệnh chạy không báo lỗi nghiêm trọng nghĩa là System Restore đang hoạt động
        return res.returncode == 0
    except Exception:
        return False
