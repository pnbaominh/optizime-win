import os
import sys
import re
import subprocess
from core.version import APP_VERSION, parse_version_tuple

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def run(cmd, check=True):
    print(f"[*] Chạy lệnh: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)

def get_next_patch_version(current_ver: str) -> str:
    nums = list(parse_version_tuple(current_ver))
    while len(nums) < 3:
        nums.append(0)
    nums[-1] += 1
    return ".".join(str(n) for n in nums)

def update_files_version(new_version: str):
    # 1. Cập nhật core/version.py
    ver_file = os.path.join("core", "version.py")
    with open(ver_file, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'APP_VERSION = ".*?"', f'APP_VERSION = "{new_version}"', content)
    with open(ver_file, "w", encoding="utf-8") as f:
        f.write(content)

    # 2. Cập nhật installer_setup.iss
    iss_file = "installer_setup.iss"
    if os.path.exists(iss_file):
        with open(iss_file, "r", encoding="utf-8") as f:
            iss_content = f.read()
        iss_content = re.sub(r'#define MyAppVersion ".*?"', f'#define MyAppVersion "{new_version}"', iss_content)
        iss_content = re.sub(r'AppVersion=.*', f'AppVersion={new_version}', iss_content)
        with open(iss_file, "w", encoding="utf-8") as f:
            f.write(iss_content)

def main():
    print("===============================================================")
    print("       QUY TRÌNH TẠO BẢN PHÁT HÀNH MỚI (RELEASE MANAGER)       ")
    print("===============================================================")
    current_ver = APP_VERSION
    suggested_ver = get_next_patch_version(current_ver)

    print(f"[*] Phiên bản hiện tại trong mã nguồn: v{current_ver}")
    user_ver = input(f"[*] Nhập phiên bản mới cần release (mặc định: {suggested_ver}): ").strip()
    new_version = user_ver if user_ver else suggested_ver
    new_version = new_version.lstrip("vV")

    tag_name = f"v{new_version}"

    print("\n---------------------------------------------------------------")
    print(f"  Chuẩn bị phát hành:")
    print(f"  - Phiên bản mới : {new_version}")
    print(f"  - Git Tag       : {tag_name}")
    print("---------------------------------------------------------------")

    # BƯỚC XÁC NHẬN BẮT BUỘC THEO YÊU CẦU CỦA NGƯỜI DÙNG
    confirm = input(f"\n❓ BẠN CÓ XÁC NHẬN TẠO BẢN RELEASE {tag_name} LÊN GITHUB KHÔNG? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("[!] Đã hủy bỏ tiến trình release theo yêu cầu của bạn.")
        return

    print("\n[*] Đang cập nhật số phiên bản vào core/version.py và installer_setup.iss...")
    update_files_version(new_version)

    # Kiểm tra git status
    print("[*] Đang chuẩn bị Git commit và Git tag...")
    try:
        run(["git", "add", "core/version.py", "installer_setup.iss"])
        run(["git", "commit", "-m", f"chore(release): bump version to {tag_name}"], check=False)
        run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])
        print(f"[*] Đã tạo git tag: {tag_name}")

        push_confirm = input(f"\n❓ Bạn có muốn đẩy (git push) tag {tag_name} lên GitHub ngay bây giờ? [y/N]: ").strip().lower()
        if push_confirm in ("y", "yes"):
            run(["git", "push", "origin", "main", "--tags"])
            print("===============================================================")
            print(f"  🎉 ĐÃ PUSH THÀNH CÔNG TAG {tag_name} LÊN GITHUB!")
            print("  GitHub Actions sẽ tự động biên dịch bộ cài đặt Inno Setup")
            print("  và phát hành bản release kèm WindowsDeepOptimizer_Setup.exe.")
            print("  Khi người dùng mở app lên, hệ thống sẽ tự động phát hiện")
            print("  và cho phép cập nhật tức thời!")
            print("===============================================================")
        else:
            print("[*] Đã tạo commit và tag trên local. Bạn có thể push thủ công bằng lệnh:")
            print(f"    git push origin main --tags")
    except Exception as e:
        print(f"[!] Lỗi trong quá trình git: {e}")

if __name__ == "__main__":
    main()
