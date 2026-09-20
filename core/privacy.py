import winreg
from typing import Tuple
from core.tweak_base import Tweak
from core.safety import backup_registry_key

def set_reg_dword(root_hkey, sub_key: str, name: str, value: int):
    """Ghi một giá trị REG_DWORD vào Registry."""
    with winreg.CreateKeyEx(root_hkey, sub_key, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)

def get_reg_dword(root_hkey, sub_key: str, name: str, default: int = None) -> int:
    """Đọc một giá trị REG_DWORD từ Registry."""
    try:
        with winreg.OpenKey(root_hkey, sub_key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            val, typ = winreg.QueryValueEx(key, name)
            if typ == winreg.REG_DWORD:
                return val
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return default

def delete_reg_value(root_hkey, sub_key: str, name: str):
    """Xóa một giá trị khỏi Registry nếu tồn tại."""
    try:
        with winreg.OpenKey(root_hkey, sub_key, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass
    except Exception:
        pass


class DisableTelemetryTweak(Tweak):
    def __init__(self):
        super().__init__(
            tweak_id="privacy_telemetry",
            name="Vô hiệu hóa Telemetry & Chẩn đoán ngầm",
            category="Quyền Riêng Tư",
            description="Giảm mức dữ liệu chẩn đoán và theo dõi telemetry của Windows gửi về Microsoft.",
            explanation=(
                "Windows gửi các thông tin chẩn đoán lỗi và hành vi sử dụng về máy chủ Microsoft.\n"
                "Khi tắt, giá trị 'AllowTelemetry' trong nhánh Policy được đặt về 0 (Mức Security/Off),\n"
                "giúp giải phóng chu kỳ CPU chạy ngầm và tiết kiệm băng thông mạng.\n"
                "Không ảnh hưởng đến Windows Update hay tính ổn định của hệ điều hành."
            ),
            is_recommended=True
        )
        self.sub_key = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
        self.val_name = "AllowTelemetry"

    def check(self) -> bool:
        val = get_reg_dword(winreg.HKEY_LOCAL_MACHINE, self.sub_key, self.val_name)
        return val == 0

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(f"HKLM\\{self.sub_key}", "telemetry")
        try:
            set_reg_dword(winreg.HKEY_LOCAL_MACHINE, self.sub_key, self.val_name, 0)
            return True, "Đã vô hiệu hóa Telemetry chẩn đoán thành công."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            delete_reg_value(winreg.HKEY_LOCAL_MACHINE, self.sub_key, self.val_name)
            return True, "Đã hoàn tác Telemetry về mặc định Windows."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


class DisableBingSearchTweak(Tweak):
    def __init__(self):
        super().__init__(
            tweak_id="privacy_bing_search",
            name="Tắt tìm kiếm Bing trong Start Menu",
            category="Quyền Riêng Tư",
            description="Chỉ tìm kiếm ứng dụng và tệp tin cục bộ trên máy, loại bỏ quảng cáo web từ Bing.",
            explanation=(
                "Mỗi khi gõ tìm ứng dụng trong thanh tìm kiếm Start Menu, Windows sẽ gửi từ khóa lên Bing\n"
                "để tìm gợi ý web, gây hiện tượng khựng giật (delay 1-2 giây) và tốn dữ liệu mạng.\n"
                "Tùy chọn này tắt tìm kiếm web trong Start Menu, giúp mở phần mềm ngay tức thì."
            ),
            is_recommended=True
        )

    def check(self) -> bool:
        val1 = get_reg_dword(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions")
        val2 = get_reg_dword(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled")
        return val1 == 1 and val2 == 0

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(r"HKCU\Software\Policies\Microsoft\Windows\Explorer", "bing_search_exp")
        backup_registry_key(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search", "bing_search_main")
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", 1)
            set_reg_dword(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", 0)
            return True, "Đã tắt tìm kiếm Bing trên Start Menu thành công."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            delete_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions")
            set_reg_dword(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", 1)
            return True, "Đã bật lại tìm kiếm Bing trong Start Menu."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


class DisableAdvertisingIdTweak(Tweak):
    def __init__(self):
        super().__init__(
            tweak_id="privacy_ad_id",
            name="Tắt mã định danh quảng cáo (Advertising ID)",
            category="Quyền Riêng Tư",
            description="Ngăn các ứng dụng theo dõi sở thích cá nhân để hiển thị quảng cáo theo mục tiêu.",
            explanation=(
                "Windows cấp cho mỗi tài khoản người dùng một mã định danh quảng cáo để các app khai thác.\n"
                "Tắt tùy chọn này bảo vệ quyền riêng tư cá nhân và chặn theo dõi danh tính số."
            ),
            is_recommended=True
        )
        self.sub_key = r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"

    def check(self) -> bool:
        val = get_reg_dword(winreg.HKEY_CURRENT_USER, self.sub_key, "Enabled")
        return val == 0

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(f"HKCU\\{self.sub_key}", "advertising_id")
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, self.sub_key, "Enabled", 0)
            return True, "Đã vô hiệu hóa Advertising ID."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, self.sub_key, "Enabled", 1)
            return True, "Đã bật lại Advertising ID theo mặc định."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


class DisableActivityFeedTweak(Tweak):
    def __init__(self):
        super().__init__(
            tweak_id="privacy_activity_history",
            name="Tắt đồng bộ lịch sử hoạt động (Activity History)",
            category="Quyền Riêng Tư",
            description="Ngăn Windows lưu trữ và gửi dữ liệu về các tệp tin/ứng dụng bạn vừa mở lên máy chủ đám mây.",
            explanation=(
                "Tính năng Activity Feed lưu lại các hoạt động làm việc của bạn để đồng bộ lên tài khoản Microsoft.\n"
                "Khi tắt tính năng này, việc ghi nhật ký ngầm được dừng lại, giảm tải ghi đĩa SSD."
            ),
            is_recommended=True
        )
        self.sub_key = r"SOFTWARE\Policies\Microsoft\Windows\System"

    def check(self) -> bool:
        val1 = get_reg_dword(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "EnableActivityFeed")
        val2 = get_reg_dword(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "PublishUserActivities")
        return val1 == 0 and val2 == 0

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(f"HKLM\\{self.sub_key}", "activity_feed")
        try:
            set_reg_dword(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "EnableActivityFeed", 0)
            set_reg_dword(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "PublishUserActivities", 0)
            set_reg_dword(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "UploadUserActivities", 0)
            return True, "Đã vô hiệu hóa đồng bộ Activity History."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            delete_reg_value(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "EnableActivityFeed")
            delete_reg_value(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "PublishUserActivities")
            delete_reg_value(winreg.HKEY_LOCAL_MACHINE, self.sub_key, "UploadUserActivities")
            return True, "Đã hoàn tác Activity History về mặc định."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


class DisableFeedbackPromptsTweak(Tweak):
    def __init__(self):
        super().__init__(
            tweak_id="privacy_feedback_prompts",
            name="Tắt thông báo hỏi ý kiến phản hồi (Feedback Prompts)",
            category="Quyền Riêng Tư",
            description="Loại bỏ các thông báo pop-up 'Bạn cảm thấy Windows hôm nay thế nào?'.",
            explanation=(
                "Windows thường xuyên kích hoạt tiến trình ngầm để đánh giá và nhắc người dùng gửi phản hồi.\n"
                "Tùy chọn này đặt tần suất hỏi phản hồi về 0 (Never), tránh làm gián đoạn công việc."
            ),
            is_recommended=True
        )
        self.sub_key = r"Software\Microsoft\Siuf\Rules"

    def check(self) -> bool:
        val = get_reg_dword(winreg.HKEY_CURRENT_USER, self.sub_key, "NumberOfSIUFInPeriod")
        return val == 0

    def apply(self) -> Tuple[bool, str]:
        backup_registry_key(f"HKCU\\{self.sub_key}", "feedback_prompts")
        try:
            set_reg_dword(winreg.HKEY_CURRENT_USER, self.sub_key, "NumberOfSIUFInPeriod", 0)
            return True, "Đã tắt nhắc nhở phản hồi thành công."
        except Exception as e:
            return False, f"Lỗi áp dụng: {e}"

    def revert(self) -> Tuple[bool, str]:
        try:
            delete_reg_value(winreg.HKEY_CURRENT_USER, self.sub_key, "NumberOfSIUFInPeriod")
            return True, "Đã khôi phục tần suất hỏi phản hồi về mặc định."
        except Exception as e:
            return False, f"Lỗi hoàn tác: {e}"


def get_privacy_tweaks() -> list[Tweak]:
    """Trả về danh sách tất cả các tùy chọn tối ưu Quyền Riêng Tư."""
    return [
        DisableTelemetryTweak(),
        DisableBingSearchTweak(),
        DisableAdvertisingIdTweak(),
        DisableActivityFeedTweak(),
        DisableFeedbackPromptsTweak()
    ]
