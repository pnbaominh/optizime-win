import os
import sys
import shutil
import subprocess
from core.version import APP_VERSION

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def find_iscc() -> str:
    """Tìm đường dẫn trình biên dịch Inno Setup (ISCC.exe)."""
    # 1. Kiểm tra trong PATH
    path_iscc = shutil.which("iscc") or shutil.which("ISCC.exe")
    if path_iscc:
        return path_iscc

    # 2. Kiểm tra các thư mục cài đặt tiêu chuẩn
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""

def build_installer():
    print("=======================================================")
    print("   TIẾN TRÌNH ĐÓNG GÓI BỘ CÀI ĐẶT WINDOWS (OBS-STYLE)  ")
    print(f"   Phiên bản: v{APP_VERSION}")
    print("=======================================================")

    exe_path = os.path.abspath(os.path.join("dist", "WindowsDeepOptimizer.exe"))
    if not os.path.exists(exe_path):
        print("[*] Chưa tìm thấy file dist/WindowsDeepOptimizer.exe. Đang build file .exe trước...")
        ret = subprocess.run([sys.executable, "build_exe.py"])
        if ret.returncode != 0:
            print("[!] Build exe thất bại. Hủy đóng gói bộ cài đặt.")
            return False

    iscc = find_iscc()
    if not iscc:
        print("[!] Không tìm thấy Inno Setup Compiler (ISCC.exe) trên máy của bạn.")
        print("    Bạn có thể cài đặt nhanh Inno Setup bằng lệnh:")
        print("    winget install JRSoftware.InnoSetup -e")
        print("\n[*] LƯU Ý: Nếu đẩy lên GitHub, GitHub Actions sẽ tự động cài Inno Setup")
        print("    và build ra file WindowsDeepOptimizer_Setup.exe đầy đủ trên Release.")
        return False

    print(f"[*] Tìm thấy Inno Setup tại: {iscc}")
    iss_file = os.path.abspath("installer_setup.iss")
    output_dir = os.path.abspath("installer_output")
    os.makedirs(output_dir, exist_ok=True)

    cmd = [iscc, f"/DMyAppVersion={APP_VERSION}", iss_file]
    print(f"[*] Đang biên dịch bộ cài đặt: {' '.join(cmd)}")

    ret = subprocess.run(cmd)
    if ret.returncode == 0:
        setup_exe = os.path.join(output_dir, "WindowsDeepOptimizer_Setup.exe")
        print("=======================================================")
        print("  🎉 ĐÓNG GÓI BỘ CÀI ĐẶT THÀNH CÔNG!")
        if os.path.exists(setup_exe):
            size_mb = round(os.path.getsize(setup_exe) / (1024 * 1024), 2)
            print(f"  File cài đặt: {setup_exe}")
            print(f"  Dung lượng:   {size_mb} MB")
            print("  Đặc tính:     Cài đặt Wizard như OBS, hỗ trợ Program Files,")
            print("                Desktop Icon, Start Menu, Gỡ cài đặt trong Settings,")
            print("                Tự phát hiện & đóng phiên bản cũ khi cập nhật.")
        print("=======================================================")
        return True
    else:
        print(f"[!] Lỗi khi biên dịch Inno Setup: Mã {ret.returncode}")
        return False

if __name__ == "__main__":
    build_installer()
