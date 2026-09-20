import os
import sys
import shutil
import subprocess
import customtkinter

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def build():
    print("=======================================================")
    print("  BẮT ĐẦU ĐÓNG GÓI WINDOWS DEEP OPTIMIZER RA FILE .EXE  ")
    print("=======================================================")

    # 1. Tìm đường dẫn thư mục gốc của customtkinter để include tài nguyên (themes/fonts)
    ctk_dir = os.path.dirname(customtkinter.__file__)
    print(f"[*] CustomTkinter assets path: {ctk_dir}")

    # Đường dẫn output
    dist_dir = os.path.abspath("dist")
    build_dir = os.path.abspath("build")

    # 2. Chuẩn bị các tham số cho PyInstaller
    # --onefile: Đóng gói toàn bộ runtime và mã nguồn thành 1 file .exe duy nhất
    # --noconsole: Không hiển thị cửa sổ cmd đen phía sau
    # --uac-admin: Tự động nhúng UAC manifest requireAdministrator vào file .exe
    # --add-data: Nạp các file giao diện của customtkinter
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--uac-admin",
        "--clean",
        "--name", "WindowsDeepOptimizer",
        f"--add-data={ctk_dir};customtkinter",
        "main.py"
    ]

    print("[*] Đang thực thi PyInstaller (Quá trình có thể mất khoảng 30-60 giây)...")
    print("    Lệnh: " + " ".join(cmd))

    ret = subprocess.run(cmd)

    if ret.returncode == 0:
        exe_path = os.path.join(dist_dir, "WindowsDeepOptimizer.exe")
        if os.path.exists(exe_path):
            size_mb = round(os.path.getsize(exe_path) / (1024 * 1024), 2)
            print("=======================================================")
            print("  BUILD THÀNH CÔNG RỰC RỠ!")
            print(f"  File thực thi: {exe_path}")
            print(f"  Kích thước: {size_mb} MB")
            print("  Đặc tính: Standalone .EXE, Tự kích hoạt UAC Administrator.")
            print("=======================================================")
        else:
            print("[!] PyInstaller báo thành công nhưng không tìm thấy file .exe trong dist/")
    else:
        print(f"[!] Lỗi khi build: Mã thoát {ret.returncode}")

if __name__ == "__main__":
    build()
