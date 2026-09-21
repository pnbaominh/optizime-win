import winreg
from typing import Tuple
from core.tweak_base import Tweak
from core.safety import backup_registry_key
from core.privacy import set_reg_dword, get_reg_dword, delete_reg_value
from core.process_utils import run_cmd

class MenuShowDelayTweak(Tweak):
    """Giảm thời gian trễ hiển thị Menu từ 400ms xuống 20ms."""
    def __init__(self):
        super().__init__(
            tweak_id="perf_menu_delay",
            name="Tối ưu độ trễ hiển thị Menu (MenuShowDelay)",
            category="Hiệu Năng & Gaming",
            description="Mở menu chuột phải và menu con tức thì không cần chờ 400ms mặc định.",
            explanation=(
                "Mặc định Windows cài đặt độ trễ 400 mili-giây trước khi bung các menu con hoặc menu chuột phải.\n"
                "Khi đặt giá trị này về 20 mili-giây, các thao tác đóng mở cửa sổ và menu sẽ phản hồi cực nhạy,\n"
                "tạo cảm giác hệ điều hành mượt mà và nhanh hơn rõ rệt."
            ),
            is_recommended=True
        )
        self.sub_key = r"Control Panel\Desktop"
        self.val_name = "MenuShowDelay"

    def check(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.sub_key, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, self.val_name)
                return str(val).strip() == "20"
        except Exception:
            return False

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(f"HKCU\\{self.sub_key}", "menu_delay")
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.sub_key, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, self.val_name, 0, winreg.REG_SZ, "20")
            return True, "Đã đặt MenuShowDelay thành 20ms."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.sub_key, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, self.val_name, 0, winreg.REG_SZ, "400")
            return True, "Đã khôi phục MenuShowDelay về 400ms."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


class DisableGameDVRTweak(Tweak):
    """Tắt tính năng ghi hình nền ngầm Xbox Game DVR để tránh giật lag khi chơi game."""
    def __init__(self):
        super().__init__(
            tweak_id="perf_game_dvr",
            name="Tắt ghi hình nền ngầm Xbox Game DVR",
            category="Hiệu Năng & Gaming",
            description="Ngăn Windows liên tục ghi hình ngầm khi chơi game, loại bỏ hiện tượng drop FPS và giật lag.",
            explanation=(
                "Tính năng Game DVR của Windows liên tục ghi lại các phút chơi game gần nhất vào bộ nhớ RAM và ổ cứng\n"
                "để người dùng có thể lưu highlight bằng phím tắt. Việc này tiêu tốn nhiều tài nguyên GPU/RAM\n"
                "và gây sụt giảm khung hình (FPS drop). Tắt tính năng này giúp game mượt mà và ổn định hơn nhiều."
            ),
            is_recommended=True
        )

    def check(self) -> bool:
        val1 = get_reg_dword(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore", "GameDVR_Enabled")
        val2 = get_reg_dword(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR")
        return val1 == 0 and val2 == 0

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(r"HKCU\System\GameConfigStore", "game_dvr_user")
        backup_registry_key(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR", "game_dvr_policy")
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore", "GameDVR_Enabled", 0)
            set_reg_dword(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0)
            return True, "Đã tắt Xbox Game DVR background recording."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore", "GameDVR_Enabled", 1)
            delete_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR")
            return True, "Đã bật lại Game DVR theo mặc định."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


class DisableStartupDelayTweak(Tweak):
    """Loại bỏ thời gian chờ 10s khi Windows khởi động ứng dụng startup."""
    def __init__(self):
        super().__init__(
            tweak_id="perf_startup_delay",
            name="Loại bỏ độ trễ khởi động ứng dụng (Startup Delay)",
            category="Hiệu Năng & Gaming",
            description="Cho phép các ứng dụng khởi động cùng Windows nạp ngay lập tức, không chờ đợi 10 giây giả định.",
            explanation=(
                "Theo mặc định từ thời ổ cứng HDD, Windows thêm một khoảng trễ ~10 giây trước khi mở các app Startup\n"
                "để tránh nghẽn ổ đĩa. Trên các máy hiện đại sử dụng SSD NVMe hoặc SATA3, khoảng chờ này là hoàn toàn vô ích.\n"
                "Loại bỏ độ trễ giúp bạn vào làm việc ngay lập tức sau khi đăng nhập."
            ),
            is_recommended=True
        )
        self.sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize"

    def check(self) -> bool:
        val = get_reg_dword(winreg.HKEY_CURRENT_USER, self.sub_key, "StartupDelayInMSec")
        return val == 0

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(f"HKCU\\{self.sub_key}", "startup_delay")
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, self.sub_key, "StartupDelayInMSec", 0)
            return True, "Đã loại bỏ Startup Delay thành công."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            delete_reg_value(winreg.HKEY_CURRENT_USER, self.sub_key, "StartupDelayInMSec")
            return True, "Đã khôi phục Startup Delay về mặc định."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


class OptimizeTcpAutoTuningTweak(Tweak):
    """Kích hoạt và tối ưu hóa TCP Window Auto-Tuning để đạt tốc độ mạng tối đa."""
    def __init__(self):
        super().__init__(
            tweak_id="perf_tcp_autotuning",
            name="Tối ưu TCP Auto-Tuning Stack",
            category="Hiệu Năng & Gaming",
            description="Đặt kích thước cửa sổ tiếp nhận TCP ở mức Normal để giải phóng toàn bộ băng thông mạng Internet.",
            explanation=(
                "TCP Window Auto-Tuning là tính năng của Windows giúp mở rộng kích thước bộ đệm nhận gói tin qua mạng.\n"
                "Trên nhiều máy tính, giá trị này bị lỗi hoặc chuyển sang trạng thái disabled/restricted,\n"
                "dẫn đến việc mạng cáp quang tốc độ cao bị bóp nghẽn xuống chỉ còn 20-30%. Đặt lại về Normal\n"
                "sẽ phục hồi tốc độ tải và giảm độ trễ khi kết nối máy chủ game."
            ),
            is_recommended=True
        )

    def check(self) -> bool:
        try:
            cmd = ["netsh", "int", "tcp", "show", "global"]
            res = run_cmd(cmd, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "Auto-Tuning Level" in line or "Tự động Điều chỉnh" in line:
                        return "normal" in line.lower()
            return False
        except Exception:
            return False

    def apply(self) -> Tuple[bool, str]:
        try:
            cmd = ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"]
            res = run_cmd(cmd, timeout=10)
            if res.returncode == 0:
                return True, "Đã thiết lập TCP Auto-Tuning Level = Normal."
            return False, res.stderr.strip() or res.stdout.strip()
        except Exception as e:
            return False, str(e)

    def revert(self) -> Tuple[bool, str]:
        try:
            cmd = ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"]
            res = run_cmd(cmd, timeout=10)
            return True, "TCP Auto-Tuning được duy trì ở mức chuẩn Normal."
        except Exception as e:
            return False, str(e)


class Win11ClassicContextMenuTweak(Tweak):
    """Khôi phục Menu chuột phải cổ điển trên Windows 11 (Bỏ 'Show more options')."""
    def __init__(self):
        super().__init__(
            tweak_id="perf_win11_classic_context",
            name="Menu chuột phải cổ điển Windows 11",
            category="Hiệu Năng & Gaming",
            description="Mở menu chuột phải đầy đủ ngay lập tức, loại bỏ nút 'Show more options' phiền toái trên Windows 11.",
            explanation=(
                "Trên Windows 11, menu chuột phải mặc định bị thu gọn khiến bạn phải nhấn thêm 'Show more options'.\n"
                "Tinh chỉnh này kích hoạt CLSID cổ điển trong Registry, giúp hiển thị toàn bộ tùy chọn ngay cú nhấp đầu tiên.\n"
                "Khởi động lại Windows Explorer để thay đổi có hiệu lực ngay tức thì."
            ),
            is_recommended=True
        )
        self.clsid_key = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"

    def check(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.clsid_key, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "")
                return val == ""
        except Exception:
            return False

    def apply(self) -> Tuple[bool, str]:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.clsid_key) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
            # Khởi động lại explorer ngầm để có hiệu lực ngay
            run_cmd(["taskkill", "/f", "/im", "explorer.exe"], timeout=5)
            run_cmd(["cmd", "/c", "start", "explorer.exe"], timeout=5)
            return True, "Đã khôi phục Menu chuột phải cổ điển Windows 11."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            parent = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.clsid_key)
            except Exception:
                pass
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, parent)
            except Exception:
                pass
            run_cmd(["taskkill", "/f", "/im", "explorer.exe"], timeout=5)
            run_cmd(["cmd", "/c", "start", "explorer.exe"], timeout=5)
            return True, "Đã khôi phục Menu chuột phải mặc định của Windows 11."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


def get_performance_tweaks() -> list[Tweak]:
    """Trả về danh sách tất cả các tùy chọn tối ưu Hiệu năng & Gaming."""
    return [
        MenuShowDelayTweak(),
        DisableGameDVRTweak(),
        DisableStartupDelayTweak(),
        OptimizeTcpAutoTuningTweak(),
        Win11ClassicContextMenuTweak()
    ]

