# ⚡ Windows Deep Optimizer (Tối Ưu Hóa Windows 10 & 11 Chuyên Sâu)

Ứng dụng tối ưu hóa hệ thống Windows 10 và 11 chuyên sâu, hiện đại, đặt **tính an toàn và tính thực chất (No-Placebo / Zero-Brick)** lên hàng đầu.

---

## 🌟 Tính Năng Nổi Bật

### 1. 🛡️ An Toàn Tuyệt Đối & Khôi Phục 100%
- **Tự động tạo System Restore Point:** Trước mỗi lần tối ưu, hệ thống tự động tạo một điểm khôi phục hoàn chỉnh của Windows.
- **Tự động sao lưu Registry:** Xuất file `.reg` sao lưu các nhánh can thiệp vào thư mục `%AppData%\WindowsDeepOptimizer\backups\`.
- **1-Click Rollback:** Nút "Hoàn tác tất cả" hoặc bật tắt từng mục để đưa hệ thống về trạng thái mặc định của Windows ngay lập tức.
- **Không nháy CMD/PowerShell:** Mọi tiến trình chạy ngầm đều được ẩn 100% bằng cờ `CREATE_NO_WINDOW`, không bao giờ bật các tab console đen lên màn hình.

### 2. 🎯 Bộ Cài Đặt Chuẩn Windows (OBS-Style) & Auto-Update Trực Tuyến
- **Trình Cài Đặt Wizard Chuyên Nghiệp:** Sử dụng Inno Setup để cài đặt vào `C:\Program Files\Windows Deep Optimizer`, hỗ trợ tạo shortcut Desktop, Start Menu và đăng ký mục Gỡ cài đặt (Uninstall) sạch sẽ trong Windows Settings.
- **Tự Động Cập Nhật Trực Tuyến (In-App Auto-Updater):** Tự động phát hiện khi có bản cập nhật mới trên GitHub Releases, hiển thị Changelog và cho phép tải, nâng cấp tự động 1-click ngay trong ứng dụng mà không cần lên web tải lại.
- **Quy Trình Release Tự Động (`release.py`):** Lập trình viên cập nhật mã nguồn có thể chạy `python release.py` để xác nhận tạo release `[y/N]`, tự động tăng số phiên bản, tạo Git tag và kích hoạt GitHub Actions build bộ cài đặt.

### 3. 🚀 Tối Ưu Thực Chất - Không Chiêu Trò Giả Dược
- **Menu Chuột Phải Cổ Điển Windows 11:** Khôi phục menu chuột phải đầy đủ kiểu Windows 10, loại bỏ nút "Show more options" phiền phức.
- **Quản Lý Ứng Dụng Khởi Động (Startup Manager):** Kiểm tra và tắt các phần mềm tự chạy ngầm cùng Windows để tăng tốc độ bật máy.
- **Tối Ưu Mạng & DNS Tốc Độ Cao:** Xóa bộ đệm DNS (`ipconfig /flushdns`) ẩn và chuyển đổi nhanh sang Cloudflare DNS (1.1.1.1) hoặc Google DNS (8.8.8.8).
- **Quyền Riêng Tư (Privacy):** Tắt Telemetry chẩn đoán ngầm, tắt tìm kiếm Bing web trong Start Menu, tắt Advertising ID, tắt Activity History.
- **Dịch Vụ Hệ Thống (Services):** Vô hiệu hóa an toàn `DiagTrack`, `dmwappushservice`, `RetailDemo`, tắt `RemoteRegistry`, tắt Scheduled Task `Compatibility Appraiser` (chống 100% Disk khi mới khởi động).
- **Hiệu Năng & Gaming (Performance):** Giảm `MenuShowDelay` về 20ms, tắt Xbox Game DVR background recording, tối ưu TCP Auto-Tuning Stack.
- **Dọn Rác & Bloatware (Clean):** Dọn dẹp an toàn thư mục tạm `%TEMP%` và `Windows\Temp`, dọn dẹp Component Store WinSxS bằng DISM, gỡ bỏ an toàn các ứng dụng rác cài sẵn.

### 4. ⚡ Siêu Tối Ưu Phần Cứng CPU, GPU & RAM (Mới Trong v1.2.0)
- **🚀 5 Tinh Chỉnh Vi Xử Lý (CPU Optimizer):**
  - **Ultimate Performance Power Plan:** Kích hoạt và chuyển sang cấu hình nguồn Ultimate Performance, loại bỏ hoàn toàn độ trễ hạ xung CPU.
  - **Win32PrioritySeparation (Foreground Boost):** Thiết lập `0x26`, ưu tiên 100% chu kỳ xung nhịp CPU cho cửa sổ ứng dụng và game đang sử dụng.
  - **CPU Core Unparking (100%):** Mở khóa toàn bộ nhân CPU (`CPMINCORES = 100`), giữ mọi nhân luôn sẵn sàng không bị ngủ ngắt quãng.
  - **MMCSS System Responsiveness:** Tối ưu hóa phân bổ 90% tài nguyên CPU cho các tác vụ đa phương tiện và gaming thời gian thực.
  - **Tắt Điều Tiết Xung Nhịp (Disable Power Throttling):** Ngăn Windows tự ý bóp nghẹt xung nhịp khi đang chạy nặng.
- **🎮 5 Tinh Chỉnh Đồ Họa (GPU Optimizer):**
  - **Lập Lịch Tăng Tốc Phần Cứng GPU (HAGS):** Kích hoạt `HwSchMode = 2` cho phép GPU trực tiếp quản lý VRAM, giảm giật khung hình và tăng FPS.
  - **Variable Refresh Rate (VRR):** Tối ưu hóa tần số quét biến thiên trong DirectX cho màn hình G-Sync / FreeSync.
  - **Chế Độ Windows Game Mode Chuyên Sâu:** Kích hoạt GameBar Registry giúp ưu tiên luồng render đồ họa.
  - **GPU Priority & Giảm Độ Trễ DWM:** Thiết lập GPU Priority = 8 và giảm độ trễ hàng đợi kết xuất DWM composition (`OverlayTestMode = 5`).
  - **Ưu Tiên Card Đồ Họa Rời Hiệu Năng Cao:** Cấu hình hệ thống DirectX luôn chỉ định GPU rời (Discrete GPU) xử lý các ứng dụng đồ họa nặng (`DefaultGpuPreference = 2`).
- **💾 Nâng Cấp Quản Trị Bộ Nhớ RAM Chuyên Sâu:**
  - **DisablePagingExecutive:** Khóa phần nhân Kernel và Drivers trong RAM vật lý, ngăn Windows tráo đổi kernel xuống swap file.
  - **SvcHostSplitThresholdInKB:** Tự động tính toán theo dung lượng RAM vật lý thực tế để gom/tách tiến trình svchost tối ưu.
  - **Auto Standby Purge Worker:** Luồng nền daemon tự động dọn dẹp Standby List và Working Sets khi RAM vượt ngưỡng 80% (kèm cooldown 120 giây).
- **🛡️ Nguyên Tắc Zero-Disk Audit:** 100% tính năng mới chỉ can thiệp CPU, GPU, RAM — tuyệt đối không can thiệp ổ đĩa lưu trữ.

---

## 📥 Tải Về & Cài Đặt (Releases)

👉 **Tải phiên bản mới nhất tại: [GitHub Releases](https://github.com/pnbaominh/optizime-win/releases)**

| Tệp Tải Về (Asset) | Định Dạng | Mô Tả |
| :--- | :--- | :--- |
| 💿 **WindowsDeepOptimizer_Setup.exe** | **Bộ Cài Đặt Wizard (Khuyên dùng)** | Cài đặt như app OBS Studio, tích hợp Start Menu, Desktop Icon và hỗ trợ tự động nâng cấp in-app. |
| ⚡ **WindowsDeepOptimizer.exe** | Standalone .EXE | Bản chạy ngay không cần cài đặt (Portable). |
| 📦 **WindowsDeepOptimizer-v*.zip** | Portable ZIP | Gói nén chứa phần mềm độc lập và mã băm kiểm tra tính toàn vẹn (SHA256). |

---

## 🛠️ Dành Cho Lập Trình Viên (Developer Guide)

### 1. Chạy mã nguồn:
```powershell
python -m pip install -r requirements.txt
python main.py
```

### 2. Kiểm thử tự động (Unit & Integration Tests):
```powershell
python -m pytest tests -v
```

### 3. Đóng gói bộ cài đặt Setup:
```powershell
# Đóng gói file standalone exe
python build_exe.py

# Đóng gói bộ cài đặt Setup dạng OBS-style (Yêu cầu Inno Setup):
python build_installer.py
```

### 4. Tạo bản Release mới lên GitHub:
```powershell
python release.py
```
> Script sẽ hỏi xác nhận: `❓ BẠN CÓ XÁC NHẬN TẠO BẢN RELEASE vX.Y.Z LÊN GITHUB KHÔNG? [y/N]`  
> Khi bạn nhấn `y`, script sẽ tự động tạo commit, gắn tag git và kích hoạt GitHub Actions build bộ cài đặt `.exe` tải lên GitHub Releases.

---

## 📂 Cấu Trúc Mã Nguồn

```
optizime win/
├── core/
│   ├── contracts.py           # Strict Data Contracts, Enums & Runtime Validators
│   ├── registry_backup.py     # Dịch vụ sao lưu & phục hồi Registry nguyên tử (JSON Snapshots)
│   ├── cpu_optimizer.py       # Bộ 5 tinh chỉnh vi xử lý CPU chuyên sâu
│   ├── gpu_optimizer.py       # Bộ 5 tinh chỉnh đồ họa GPU chuyên sâu
│   ├── ram_optimizer.py       # DisablePagingExecutive, SvcHostSplit, AutoStandbyPurgeWorker
│   ├── memory_optimizer.py    # Thu gọn Working Sets & Standby List NT Native API
│   ├── network_optimizer.py   # Xóa DNS cache & cấu hình Cloudflare/Google DNS
│   ├── process_utils.py       # Chạy tiến trình ẩn 100%, ngăn chặn hiện tab CMD
│   ├── version.py             # Định nghĩa phiên bản tập trung (v1.2.0)
│   ├── updater.py             # Kiểm tra cập nhật GitHub Releases & tải installer
│   ├── startup_manager.py     # Quản lý ứng dụng khởi động cùng Windows
│   ├── safety.py              # System Restore Point & Registry Backup
│   ├── sys_info.py            # Nhận diện Windows 10/11, kiểm tra quyền Admin
│   ├── tweak_base.py          # Abstract Base Class cho Tweak
│   ├── privacy.py             # Tinh chỉnh Telemetry & Quyền riêng tư
│   ├── services.py            # Quản lý Dịch vụ & Scheduled Tasks an toàn
│   ├── performance.py         # Classic Context Menu, TCP stack, Xbox DVR, delay
│   ├── cleaner.py             # Dọn file tạm, DISM WinSxS & Bloatware
│   └── engine.py              # Bộ điều phối trung tâm quản lý toàn bộ tweaks
├── ui/
│   ├── theme.py               # Màu sắc Dark Mode Fluent Design
│   ├── components.py          # TweakCard, StatBox
│   ├── cpu_gpu_tab.py         # Giao diện Tab "⚡ Tối Ưu CPU & GPU" chuẩn Atomic Design
│   ├── update_dialog.py       # Pop-up thông báo bản cập nhật mới & tải %
│   └── main_window.py         # Giao diện chính 11 tab & Auto-update
├── tests/
│   ├── test_contracts_and_backup.py      # Unit tests cho contracts & backup service
│   ├── test_cpu_optimizer.py             # Unit tests cho 5 tinh chỉnh CPU
│   ├── test_gpu_optimizer.py             # Unit tests cho 5 tinh chỉnh GPU
│   ├── test_ram_optimizer_upgrade.py     # Unit tests cho nâng cấp RAM & daemon worker
│   ├── test_integration_workflow.py     # Integration tests & Zero-Disk Constraint audit
│   ├── test_core.py                      # Unit tests các tinh chỉnh cốt lõi
│   ├── test_memory_optimizer.py          # Unit tests memory purge NT API
│   └── test_network_optimizer.py         # Unit tests DNS & Network
├── build_exe.py               # Đóng gói PyInstaller ra file .exe độc lập
├── build_installer.py         # Đóng gói Inno Setup tạo file cài đặt chuẩn OBS
├── release.py                 # Tool release có xác nhận [y/N] và tự động tag GitHub
├── installer_setup.iss        # Cấu hình Inno Setup chuẩn OBS-style
├── requirements.txt           # Thư viện Python phụ thuộc
├── main.py                    # Điểm khởi chạy ứng dụng với AppMutex & UAC
└── README.md                  # Tài liệu hướng dẫn sử dụng
```
