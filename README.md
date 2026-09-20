# ⚡ Windows Deep Optimizer (Tối Ưu Hóa Windows 10 & 11 Chuyên Sâu)

Ứng dụng tối ưu hóa hệ thống Windows 10 và 11 chuyên sâu, hiện đại, đặt **tính an toàn và tính thực chất (No-Placebo / Zero-Brick)** lên hàng đầu.

---

## 🌟 Tính Năng Nổi Bật

### 1. 🛡️ An Toàn Tuyệt Đối (Safety First)
- **Tự động tạo System Restore Point:** Trước mỗi lần tối ưu, hệ thống tự động tạo một điểm khôi phục hoàn chỉnh của Windows.
- **Tự động sao lưu Registry:** Xuất file `.reg` sao lưu các nhánh can thiệp vào thư mục `%AppData%\WindowsDeepOptimizer\backups\`.
- **1-Click Rollback:** Nút "Hoàn tác tất cả" hoặc bật tắt từng mục để đưa hệ thống về trạng thái mặc định của Windows ngay lập tức.

### 2. 🎯 Thực Chất - Nói Không Với "Giả Dược" (No Snake-oil)
- **Không dọn RAM ảo:** Tuyệt đối không dùng lệnh `EmptyWorkingSet` (chiêu trò làm rỗng RAM tạm thời để Windows đẩy dữ liệu xuống ổ cứng, gây khựng giật).
- **Không can thiệp bừa bãi:** Không bao giờ tắt Windows Update, Windows Defender, DCOM, RPC hay Plug & Play.
- **Tối ưu chuẩn kỹ thuật:**
  - **Quyền Riêng Tư (Privacy):** Tắt Telemetry chẩn đoán ngầm, tắt tìm kiếm Bing web trong Start Menu (mở app tức thì không delay), tắt Advertising ID, tắt Activity History.
  - **Dịch Vụ Hệ Thống (Services):** Vô hiệu hóa an toàn `DiagTrack`, `dmwappushservice`, `RetailDemo`, tắt `RemoteRegistry` để tăng cường bảo mật mạng, tắt Scheduled Task `Compatibility Appraiser` (chống 100% Disk khi mới khởi động).
  - **Hiệu Năng & Gaming (Performance):** Giảm `MenuShowDelay` từ 400ms xuống 20ms (menu chuột phải bung tức thì), tắt Xbox Game DVR background recording (loại bỏ drop FPS và micro-stutter khi chơi game), loại bỏ Startup Delay 10s, tối ưu TCP Auto-Tuning Stack.
  - **Dọn Rác & Bloatware (Clean):** Dọn dẹp an toàn thư mục tạm `%TEMP%` và `Windows\Temp`, dọn dẹp Component Store WinSxS bằng lệnh Microsoft DISM (`startcomponentcleanup`), gỡ bỏ an toàn các ứng dụng rác cài sẵn (Bing News, Weather, Disney+, TikTok shortcuts, Solitaire...).

### 3. 🎨 Giao Diện Tối Giản & Trực Quan (Fluent Dark Mode)
- Thiết kế theo phong cách Fluent Design của Windows 11, Dark Mode mặc định dịu mắt.
- Mỗi tùy chọn đều có công tắc (Switch Toggle) kèm nút **"Xem giải thích chi tiết"** nêu rõ cơ chế hoạt động, ai nên bật và cách hoàn tác.
- Bảng điều khiển KPI hiển thị dung lượng ổ C: và số lượng mục đã tối ưu theo thời gian thực.
- Cửa sổ Live Log Console hiển thị chi tiết mọi hành động can thiệp.

---

## 🚀 Hướng Dẫn Sử Dụng

### Chạy trực tiếp từ mã nguồn Python
Yêu cầu: Python 3.10+ (Đã hỗ trợ hoàn hảo Python 3.14)
```powershell
# Cài đặt thư viện cần thiết
pip install -r requirements.txt

# Khởi chạy ứng dụng (Sẽ tự động kích hoạt quyền Administrator qua UAC)
python main.py
```

### Chạy Unit Test kiểm thử hệ thống
```powershell
python -m unittest tests/test_core.py
```

---

## 📦 Đóng Gói Thành File .EXE Độc Lập

### Cách 1: Tạo file Standalone .EXE (Chạy ngay không cần cài đặt)
Chạy script đóng gói tự động:
```powershell
python build_exe.py
```
Sau khi hoàn tất, file thực thi sẽ nằm tại:
`dist\WindowsDeepOptimizer.exe`
- Đã được nhúng sẵn **UAC Manifest (`requireAdministrator`)**, khi người dùng click đúp mở app, Windows sẽ tự động hiện hộp thoại xác nhận Admin chuẩn của hệ điều hành.

### Cách 2: Tạo bộ cài đặt Setup Installer (Inno Setup)
Mở file [`installer_setup.iss`](file:///C:/Users/Bim/Documents/optizime%20win/installer_setup.iss) bằng công cụ Inno Setup Compiler và bấm **Compile** (hoặc chạy lệnh `iscc installer_setup.iss`).
File cài đặt hoàn chỉnh `WindowsDeepOptimizer_Setup_v1.0.exe` sẽ được tạo ra với shortcut Desktop và tính năng gỡ cài đặt sạch sẽ trong Control Panel.

---

## 📂 Cấu Trúc Mã Nguồn

```
optizime win/
├── core/
│   ├── safety.py          # Lõi an toàn: System Restore Point & Registry Backup
│   ├── sys_info.py        # Nhận diện Windows 10/11, kiểm tra quyền Admin & ổ đĩa
│   ├── tweak_base.py      # Abstract Base Class cho Tweak (check, apply, revert)
│   ├── privacy.py         # Module tinh chỉnh Telemetry & Quyền riêng tư
│   ├── services.py        # Module quản lý Dịch vụ & Scheduled Tasks an toàn
│   ├── performance.py     # Module tối ưu độ trễ menu, TCP stack, Xbox DVR
│   ├── cleaner.py         # Module dọn file tạm, DISM WinSxS & Bloatware
│   └── engine.py          # Bộ điều phối trung tâm quản lý toàn bộ tweaks
├── ui/
│   ├── theme.py           # Định nghĩa màu sắc Dark Mode Fluent Design
│   ├── components.py      # TweakCard, StatBox và các thành phần UI tái sử dụng
│   └── main_window.py     # Giao diện chính đầy đủ tính năng và Live Console
├── tests/
│   └── test_core.py       # Unit tests kiểm tra tự động
├── build_exe.py           # Script tự động đóng gói PyInstaller ra file .exe
├── installer_setup.iss    # Cấu hình Inno Setup tạo file cài đặt
├── requirements.txt       # Danh sách thư viện Python phụ thuộc
├── main.py                # Điểm khởi chạy ứng dụng với UAC Auto-Elevation
└── README.md              # Tài liệu hướng dẫn sử dụng
```

---

## 📜 Giấy Phép & Tuyên Bố
Dự án được xây dựng với mục tiêu mang lại trải nghiệm Windows sạch sẽ, an toàn và mượt mà nhất cho người dùng. Mọi can thiệp đều minh bạch và có thể hoàn tác 100%.
