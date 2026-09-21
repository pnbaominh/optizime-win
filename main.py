import sys
import os
import ctypes

# Thêm đường dẫn thư mục gốc vào sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.sys_info import is_admin, elevate_if_not_admin

# Tạo AppMutex cho phép Inno Setup và Auto-Updater nhận diện tiến trình đang chạy
_APP_MUTEX = None
def acquire_mutex():
    global _APP_MUTEX
    try:
        _APP_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "WindowsDeepOptimizerMutex")
    except Exception:
        pass

def main():
    acquire_mutex()

    # Kiểm tra và tự động kích hoạt quyền Administrator qua UAC nếu chưa có
    if not is_admin():
        elevated = elevate_if_not_admin()
        if elevated:
            sys.exit(0)

    # Khởi chạy giao diện chính
    from ui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
