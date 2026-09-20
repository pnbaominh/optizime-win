import os
import shutil
import subprocess
from typing import Tuple, List, Dict

SAFE_BLOATWARE_LIST = [
    {"id": "Microsoft.BingNews", "name": "Tin tức Bing (Bing News)", "desc": "Ứng dụng hiển thị tin tức tổng hợp của Microsoft."},
    {"id": "Microsoft.BingWeather", "name": "Thời tiết Bing (Bing Weather)", "desc": "Ứng dụng dự báo thời tiết tích hợp."},
    {"id": "Microsoft.GetHelp", "name": "Trợ giúp (Get Help)", "desc": "Ứng dụng hỏi đáp trợ giúp cơ bản."},
    {"id": "Microsoft.Getstarted", "name": "Mẹo & Bắt đầu (Tips)", "desc": "Ứng dụng giới thiệu tính năng cho người mới."},
    {"id": "Microsoft.MicrosoftSolitaireCollection", "name": "Solitaire Game Collection", "desc": "Bộ trò chơi bài cài sẵn."},
    {"id": "Clipchamp.Clipchamp", "name": "Clipchamp Video Editor", "desc": "Trình chỉnh sửa video web cài sẵn của Windows 11."},
    {"id": "Disney.37853FC22B2CE", "name": "Disney+ (Quảng cáo cài sẵn)", "desc": "Phím tắt ứng dụng Disney+ được tài trợ."},
    {"id": "BytedancePte.Ltd.TikTok", "name": "TikTok (Quảng cáo cài sẵn)", "desc": "Phím tắt ứng dụng TikTok được tài trợ."},
    {"id": "SpotifyAB.SpotifyMusic", "name": "Spotify (Bản cài sẵn từ Store)", "desc": "Bản cài đặt sẵn của Spotify từ Microsoft Store."},
]

def clean_directory_contents(dir_path: str) -> Tuple[int, int]:
    """
    Xóa an toàn các tệp tin và thư mục con trong một thư mục tạm.
    Bỏ qua các tệp tin đang bị khóa bởi tiến trình đang chạy.
    Trả về: (Số tệp tin đã xóa, Tổng dung lượng giải phóng tính bằng bytes).
    """
    files_deleted = 0
    bytes_freed = 0

    if not os.path.exists(dir_path):
        return 0, 0

    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                size = os.path.getsize(item_path)
                os.remove(item_path)
                files_deleted += 1
                bytes_freed += size
            elif os.path.isdir(item_path):
                # Tính kích thước trước khi xóa
                for root, _, files in os.walk(item_path):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            bytes_freed += os.path.getsize(fp)
                            files_deleted += 1
                        except Exception:
                            pass
                shutil.rmtree(item_path, ignore_errors=True)
        except (PermissionError, OSError):
            # Tệp đang được Windows hoặc phần mềm khác sử dụng, bỏ qua an toàn
            continue
        except Exception:
            continue

    return files_deleted, bytes_freed

def clean_system_temp_files() -> Dict[str, any]:
    """Dọn dẹp thư mục Temp của người dùng và Temp của hệ thống Windows."""
    user_temp = os.environ.get("TEMP", "")
    win_temp = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")

    total_files = 0
    total_bytes = 0

    if user_temp and os.path.exists(user_temp):
        f1, b1 = clean_directory_contents(user_temp)
        total_files += f1
        total_bytes += b1

    if win_temp and os.path.exists(win_temp):
        f2, b2 = clean_directory_contents(win_temp)
        total_files += f2
        total_bytes += b2

    mb_freed = round(total_bytes / (1024 * 1024), 2)
    return {
        "success": True,
        "files_deleted": total_files,
        "bytes_freed": total_bytes,
        "mb_freed": mb_freed,
        "message": f"Đã dọn dẹp thành công {total_files} tệp tạm, giải phóng {mb_freed} MB bộ nhớ đệm!"
    }

def run_dism_component_cleanup() -> Tuple[bool, str]:
    """
    Chạy lệnh chính thức của Microsoft để dọn dẹp Component Store (thư mục WinSxS):
    dism.exe /online /cleanup-image /startcomponentcleanup
    """
    try:
        cmd = ["dism.exe", "/online", "/cleanup-image", "/startcomponentcleanup"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode == 0:
            return True, "Dọn dẹp Windows Component Store (WinSxS) hoàn tất thành công!"
        return False, f"Lỗi DISM: {res.stderr.strip() or res.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Quá thời gian thực thi DISM (Timeout)."
    except Exception as e:
        return False, str(e)

def get_installed_bloatware() -> List[Dict[str, any]]:
    """Kiểm tra danh sách các ứng dụng rác đang thực sự được cài đặt trên máy."""
    installed = []
    for app in SAFE_BLOATWARE_LIST:
        app_id = app["id"]
        ps_cmd = f"Get-AppxPackage -Name '*{app_id}*' -ErrorAction SilentlyContinue"
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            is_present = bool(res.stdout.strip())
        except Exception:
            is_present = False
        
        installed.append({
            "id": app["id"],
            "name": app["name"],
            "desc": app["desc"],
            "is_installed": is_present
        })
    return installed

def remove_bloatware_package(package_id: str) -> Tuple[bool, str]:
    """Gỡ bỏ an toàn một gói ứng dụng AppX khỏi tài khoản hiện tại."""
    ps_cmd = f"Get-AppxPackage -Name '*{package_id}*' -ErrorAction SilentlyContinue | Remove-AppxPackage"
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if res.returncode == 0:
            return True, f"Đã gỡ bỏ {package_id} thành công."
        return False, f"Lỗi gỡ bỏ: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, str(e)
