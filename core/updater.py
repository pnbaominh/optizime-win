import os
import sys
import json
import urllib.request
import urllib.error
import tempfile
import threading
from typing import Optional, Dict, Any, Callable
from core.version import APP_VERSION, GITHUB_LATEST_RELEASE_URL, is_newer_version
from core.process_utils import run_cmd

class UpdateChecker:
    @staticmethod
    def check_for_updates() -> Optional[Dict[str, Any]]:
        """
        Kiểm tra GitHub Releases API để tìm bản cập nhật mới nhất.
        Trả về dictionary chứa thông tin bản cập nhật nếu có bản mới, ngược lại trả về None.
        """
        headers = {
            "User-Agent": "WindowsDeepOptimizer-AutoUpdater",
            "Accept": "application/vnd.github.v3+json"
        }
        req = urllib.request.Request(GITHUB_LATEST_RELEASE_URL, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    remote_tag = data.get("tag_name", "")
                    
                    if is_newer_version(remote_tag, APP_VERSION):
                        # Tìm asset bộ cài đặt .exe ưu tiên Setup
                        assets = data.get("assets", [])
                        download_url = None
                        installer_name = None
                        installer_size = 0

                        # Tìm file có chữ Setup trước
                        for asset in assets:
                            name = asset.get("name", "")
                            if name.endswith(".exe") and "setup" in name.lower():
                                download_url = asset.get("browser_download_url")
                                installer_name = name
                                installer_size = asset.get("size", 0)
                                break

                        # Nếu không có Setup.exe thì lấy bất kỳ file .exe nào
                        if not download_url:
                            for asset in assets:
                                name = asset.get("name", "")
                                if name.endswith(".exe"):
                                    download_url = asset.get("browser_download_url")
                                    installer_name = name
                                    installer_size = asset.get("size", 0)
                                    break

                        return {
                            "has_update": True,
                            "current_version": APP_VERSION,
                            "latest_version": remote_tag,
                            "release_name": data.get("name", remote_tag),
                            "changelog": data.get("body", "Không có ghi chú phát hành."),
                            "published_at": data.get("published_at", ""),
                            "html_url": data.get("html_url", ""),
                            "download_url": download_url,
                            "installer_name": installer_name,
                            "size_bytes": installer_size
                        }
                    else:
                        return {
                            "has_update": False,
                            "status": "latest",
                            "current_version": APP_VERSION,
                            "latest_version": remote_tag
                        }
            return {"has_update": False, "status": "unknown"}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {
                    "has_update": False,
                    "status": "not_found",
                    "error": (
                        "Không tìm thấy bản phát hành trên GitHub (Mã lỗi 404).\n\n"
                        "Vui lòng kiểm tra 2 điều sau:\n"
                        "1. GitHub Actions cần khoảng 2-3 phút để biên dịch xong sau khi push tag.\n"
                        "2. Repository GitHub phải ở chế độ PUBLIC (Công khai). Nếu repo đang ở Private, GitHub sẽ từ chối cung cấp bản cập nhật cho ứng dụng."
                    )
                }
            return {
                "has_update": False,
                "status": "http_error",
                "error": f"Lỗi phản hồi từ GitHub: HTTP {e.code} - {e.reason}"
            }
        except Exception as e:
            return {
                "has_update": False,
                "status": "network_error",
                "error": f"Không thể kết nối đến máy chủ GitHub: {e}"
            }

def download_and_install_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    completion_callback: Optional[Callable[[], None]] = None,
    error_callback: Optional[Callable[[str], None]] = None
):
    """
    Tải file cài đặt về thư mục %TEMP% và chạy tiến trình cài đặt tự động.
    """
    def _worker():
        try:
            temp_dir = tempfile.gettempdir()
            target_installer = os.path.join(temp_dir, "WindowsDeepOptimizer_Update.exe")

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "WindowsDeepOptimizer-AutoUpdater"}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB

                with open(target_installer, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and progress_callback:
                            percent = (downloaded / total_size) * 100
                            progress_callback(downloaded, total_size, percent)

            if completion_callback:
                completion_callback()

            # Chạy file cài đặt với tham số đóng ứng dụng cũ và khởi động lại
            # Nếu là Inno Setup: /SILENT hoặc /VERYSILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
            import subprocess
            if os.path.exists(target_installer):
                subprocess.Popen(
                    [target_installer, "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
                    shell=True
                )
                # Thoát ứng dụng hiện tại để trình cài đặt ghi đè file
                os._exit(0)

        except Exception as e:
            if error_callback:
                error_callback(str(e))

    threading.Thread(target=_worker, daemon=True).start()
