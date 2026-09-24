"""
Định nghĩa tập trung thông tin phiên bản ứng dụng và cấu hình Repository.
"""

APP_NAME = "Windows Deep Optimizer"
APP_VERSION = "1.1.4"
REPO_OWNER = "pnbaominh"
REPO_NAME = "optizime-win"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
GITHUB_REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"

def parse_version_tuple(ver_str: str) -> tuple:
    """Chuyển chuỗi phiên bản dạng 'v1.2.3' hoặc '1.2.3' thành tuple các số (1, 2, 3) để so sánh."""
    clean = ver_str.strip().lstrip("vV")
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            # Bỏ qua hậu tố như -beta, -rc
            digits = "".join(c for c in p if c.isdigit())
            parts.append(int(digits) if digits else 0)
    return tuple(parts)

def is_newer_version(remote_ver: str, current_ver: str = APP_VERSION) -> bool:
    """Trả về True nếu phiên bản trên remote lớn hơn phiên bản hiện tại."""
    try:
        return parse_version_tuple(remote_ver) > parse_version_tuple(current_ver)
    except Exception:
        return False
