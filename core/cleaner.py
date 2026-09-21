import os
import shutil
from typing import Tuple, List, Dict
from core.process_utils import run_cmd

SAFE_BLOATWARE_LIST = [
    {"id": "Microsoft.YourPhone", "name": "Phone Link (Liên kết điện thoại)", "desc": "Đồng bộ điện thoại với Windows chạy ngầm liên tục."},
    {"id": "Microsoft.WindowsFeedbackHub", "name": "Trung tâm phản hồi (Feedback Hub)", "desc": "Ứng dụng gửi ý kiến phản hồi về Microsoft."},
    {"id": "Microsoft.GetHelp", "name": "Trợ giúp (Get Help)", "desc": "Ứng dụng hỏi đáp trợ giúp cơ bản."},
    {"id": "Microsoft.Getstarted", "name": "Mẹo & Bắt đầu (Tips)", "desc": "Ứng dụng giới thiệu tính năng cho người mới."},
    {"id": "Clipchamp.Clipchamp", "name": "Clipchamp Video Editor", "desc": "Trình chỉnh sửa video web cài sẵn của Windows 11."},
    {"id": "Microsoft.BingNews", "name": "Tin tức Bing (Bing News)", "desc": "Ứng dụng hiển thị tin tức tổng hợp của Microsoft."},
    {"id": "Microsoft.BingWeather", "name": "Thời tiết Bing (Bing Weather)", "desc": "Ứng dụng dự báo thời tiết tích hợp."},
    {"id": "Microsoft.MicrosoftSolitaireCollection", "name": "Solitaire Game Collection", "desc": "Bộ trò chơi bài cài sẵn."},
    {"id": "SpotifyAB.SpotifyMusic", "name": "Spotify (Bản cài sẵn từ Store)", "desc": "Bản cài đặt sẵn của Spotify từ Microsoft Store."},
    {"id": "Disney.37853FC22B2CE", "name": "Disney+ (Quảng cáo cài sẵn)", "desc": "Phím tắt ứng dụng Disney+ được tài trợ."},
    {"id": "BytedancePte.Ltd.TikTok", "name": "TikTok (Quảng cáo cài sẵn)", "desc": "Phím tắt ứng dụng TikTok được tài trợ."},
    {"id": "Microsoft.ZuneMusic", "name": "Media Player (Groove Music cũ)", "desc": "Trình nghe nhạc cài sẵn."},
    {"id": "Microsoft.ZuneVideo", "name": "Phim & TV (Movies & TV)", "desc": "Trình xem video cài sẵn."}
]

def clean_directory_contents(dir_path: str) -> Tuple[int, int]:
    """
    Xóa an toàn và cực nhanh các tệp tin và thư mục con trong một thư mục tạm bằng os.scandir.
    Bỏ qua các tệp tin đang bị khóa bởi tiến trình đang chạy.
    Trả về: (Số tệp tin đã xóa, Tổng dung lượng giải phóng tính bằng bytes).
    """
    files_deleted = 0
    bytes_freed = 0

    if not os.path.exists(dir_path):
        return 0, 0

    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        try:
                            sz = entry.stat().st_size
                            os.remove(entry.path)
                            files_deleted += 1
                            bytes_freed += sz
                        except Exception:
                            pass
                    elif entry.is_dir(follow_symlinks=False):
                        try:
                            shutil.rmtree(entry.path, ignore_errors=True)
                            files_deleted += 1
                            bytes_freed += 512 * 1024  # ước tính 512KB/thư mục
                        except Exception:
                            pass
                except Exception:
                    continue
    except Exception:
        pass

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

def scan_system_temp_files() -> Dict[str, any]:
    """Quét và tính toán nhanh dung lượng các file tạm hiện có."""
    user_temp = os.environ.get("TEMP", "")
    win_temp = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")

    total_files = 0
    total_bytes = 0

    for d in (user_temp, win_temp):
        if d and os.path.exists(d):
            try:
                with os.scandir(d) as it:
                    for entry in it:
                        try:
                            if entry.is_file(follow_symlinks=False):
                                total_files += 1
                                total_bytes += entry.stat().st_size
                            elif entry.is_dir(follow_symlinks=False):
                                total_files += 1
                                total_bytes += 512 * 1024
                        except Exception:
                            pass
            except Exception:
                pass

    mb = round(total_bytes / (1024 * 1024), 2)
    return {
        "files": total_files,
        "bytes": total_bytes,
        "mb": mb,
        "message": f"Phát hiện khoảng {total_files} tệp tạm (~{mb} MB) có thể dọn dẹp."
    }

def run_dism_component_cleanup() -> Tuple[bool, str]:
    """
    Chạy lệnh chính thức của Microsoft để dọn dẹp Component Store (thư mục WinSxS):
    dism.exe /online /cleanup-image /startcomponentcleanup
    """
    try:
        cmd = ["dism.exe", "/online", "/cleanup-image", "/startcomponentcleanup"]
        res = run_cmd(cmd, timeout=300)
        if res.returncode == 0:
            return True, "Dọn dẹp Windows Component Store (WinSxS) hoàn tất thành công!"
        return False, f"Lỗi DISM: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, str(e)

def get_installed_bloatware() -> List[Dict[str, any]]:
    """Kiểm tra danh sách các ứng dụng rác đang thực sự được cài đặt trên máy bằng 1 lệnh duy nhất."""
    installed_names = set()
    try:
        ps_cmd = "Get-AppxPackage | Select-Object -ExpandProperty Name"
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
        res = run_cmd(cmd, timeout=10)
        if res.returncode == 0 and res.stdout:
            for line in res.stdout.splitlines():
                clean_name = line.strip().lower()
                if clean_name:
                    installed_names.add(clean_name)
    except Exception:
        pass

    installed = []
    for app in SAFE_BLOATWARE_LIST:
        app_id_lower = app["id"].lower()
        # So khớp id trong danh sách AppX đã cài đặt
        is_present = any(app_id_lower in name for name in installed_names)
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
        res = run_cmd(cmd, timeout=25)
        if res.returncode == 0:
            return True, f"Đã gỡ bỏ {package_id} thành công."
        return False, f"Lỗi gỡ bỏ: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, str(e)
