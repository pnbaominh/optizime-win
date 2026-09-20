import sys
import os

# Thêm đường dẫn thư mục gốc vào sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.sys_info import is_admin, elevate_if_not_admin

def main():
    # Kiểm tra và tự động kích hoạt quyền Administrator qua UAC nếu chưa có
    if not is_admin():
        # Thử tự động nâng quyền
        elevated = elevate_if_not_admin()
        if elevated:
            # Tiến trình con đã được khởi chạy với quyền Admin, thoát tiến trình cũ
            sys.exit(0)

    # Khởi chạy giao diện chính
    from ui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
