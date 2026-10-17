import winreg
from typing import Tuple
from core.tweak_base import Tweak
from core.process_utils import run_cmd

def get_service_start_type(service_name: str) -> str:
    """Lấy kiểu khởi động của Windows Service qua Registry và lệnh sc.exe qc."""
    # 1. Thử đọc trực tiếp từ Registry (nhanh và chính xác tuyệt đối)
    try:
        sub_key = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            val, typ = winreg.QueryValueEx(key, "Start")
            if val == 4:
                return "DISABLED"
            elif val == 3:
                return "MANUAL"
            elif val == 2:
                return "AUTO"
    except Exception:
        pass

    # 2. Dự phòng qua lệnh sc.exe qc
    try:
        cmd = ["sc.exe", "qc", service_name]
        res = run_cmd(cmd, timeout=5)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "START_TYPE" in line:
                    line_upper = line.upper()
                    if "DISABLED" in line_upper:
                        return "DISABLED"
                    elif "DEMAND_START" in line_upper:
                        return "MANUAL"
                    elif "AUTO_START" in line_upper:
                        return "AUTO"
        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"

def set_service_start_type(service_name: str, start_type: str) -> Tuple[bool, str]:
    """
    Đặt kiểu khởi động cho Windows Service:
    start_type: 'disabled', 'demand' (manual), hoặc 'auto'
    """
    start_val_map = {
        "disabled": 4,
        "demand": 3,
        "manual": 3,
        "auto": 2
    }
    target_val = start_val_map.get(start_type.lower(), 3)
    reg_ok = False

    # 1. Ghi trực tiếp vào Registry
    try:
        sub_key = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, target_val)
            reg_ok = True
    except Exception:
        reg_ok = False

    # 2. Chạy lệnh sc.exe config
    sc_start = "demand" if start_type.lower() in ("manual", "demand") else start_type.lower()
    cmd = ["sc.exe", "config", service_name, f"start= {sc_start}"]
    res = run_cmd(cmd, timeout=10)

    # 3. Dừng dịch vụ nếu chọn disabled
    if start_type.lower() == "disabled":
        run_cmd(["sc.exe", "stop", service_name], timeout=5)

    if reg_ok or res.returncode == 0:
        return True, f"Dịch vụ {service_name} đã được đặt thành {start_type}."
    else:
        err = res.stderr.strip() or res.stdout.strip() or "Yêu cầu quyền Administrator."
        return False, f"Lỗi cấu hình {service_name}: {err}"


class ServiceTweak(Tweak):
    """Lớp Tweak chuyên biệt cho cấu hình Windows Service."""
    def __init__(
        self,
        tweak_id: str,
        name: str,
        service_name: str,
        description: str,
        explanation: str,
        default_start_type: str = "auto",
        is_recommended: bool = True
    ):
        super().__init__(
            tweak_id=tweak_id,
            name=name,
            category="Dịch Vụ Hệ Thống",
            description=description,
            explanation=explanation,
            is_recommended=is_recommended
        )
        self.service_name = service_name
        self.default_start_type = default_start_type

    def check(self) -> bool:
        st = get_service_start_type(self.service_name)
        return st == "DISABLED"

    def apply(self) -> Tuple[bool, str]:
        return set_service_start_type(self.service_name, "disabled")

    def revert(self) -> Tuple[bool, str]:
        return set_service_start_type(self.service_name, self.default_start_type)


class DisableDiagTrackTweak(ServiceTweak):
    def __init__(self):
        super().__init__(
            tweak_id="service_diagtrack",
            name="Tắt dịch vụ Connected User Experiences & Telemetry",
            service_name="DiagTrack",
            description="Dịch vụ thu thập thông tin hoạt động và chẩn đoán liên tục của Windows.",
            explanation=(
                "Dịch vụ 'DiagTrack' chạy tiến trình 'diagtrack.dll' ngầm trong svchost.exe,\n"
                "thường xuyên quét hệ thống và ghi log chẩn đoán lỗi gửi đi.\n"
                "Tắt dịch vụ này giúp giảm tải CPU ngầm và không ảnh hưởng đến bất kỳ phần mềm thông thường nào."
            ),
            default_start_type="auto",
            is_recommended=True
        )


class DisableWapPushTweak(ServiceTweak):
    def __init__(self):
        super().__init__(
            tweak_id="service_dmwappush",
            name="Tắt dịch vụ WAP Push Service",
            service_name="dmwappushservice",
            description="Dịch vụ tiếp nhận và định tuyến các tin nhắn WAP Push liên quan đến chẩn đoán viễn thông.",
            explanation=(
                "Dịch vụ 'dmwappushservice' được sử dụng để điều hướng dữ liệu theo dõi trên Windows.\n"
                "Đối với máy tính cá nhân (PC/Laptop), dịch vụ này hoàn toàn dư thừa và an toàn 100% khi tắt."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableRetailDemoTweak(ServiceTweak):
    def __init__(self):
        super().__init__(
            tweak_id="service_retail_demo",
            name="Tắt dịch vụ Retail Demo Service",
            service_name="RetailDemo",
            description="Dịch vụ chạy chế độ trưng bày trải nghiệm dành cho cửa hàng bán lẻ máy tính.",
            explanation=(
                "Chế độ 'Retail Demo' chỉ dùng cho máy mẫu tại quầy triển lãm/showroom bán lẻ.\n"
                "Người dùng cá nhân tuyệt đối không cần dịch vụ này chạy ngầm."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableRemoteRegistryTweak(ServiceTweak):
    def __init__(self):
        super().__init__(
            tweak_id="service_remote_registry",
            name="Tắt dịch vụ Remote Registry (Gia tăng bảo mật)",
            service_name="RemoteRegistry",
            description="Ngăn chặn người dùng hoặc thiết bị từ xa qua mạng LAN sửa đổi Registry trên máy bạn.",
            explanation=(
                "Dịch vụ này cho phép người dùng từ xa chỉnh sửa các khóa Registry.\n"
                "Vô hiệu hóa dịch vụ này là tiêu chuẩn bảo mật được khuyến nghị bởi các chuyên gia an ninh mạng,\n"
                "giúp chống lại các cuộc tấn công leo thang đặc quyền trong mạng nội bộ."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableMapsBrokerTweak(ServiceTweak):
    def __init__(self):
        super().__init__(
            tweak_id="service_maps_broker",
            name="Tắt dịch vụ Downloaded Maps Manager",
            service_name="MapsBroker",
            description="Quản lý việc tải về và cập nhật bản đồ ngoại tuyến của ứng dụng Windows Maps.",
            explanation=(
                "Nếu bạn sử dụng Google Maps hoặc trình duyệt web thay vì app Maps tích hợp của Windows,\n"
                "dịch vụ này không cần thiết phải duy trì tiến trình chạy ngầm."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableCompatibilityAppraiserTweak(Tweak):
    """Tắt Scheduled Task Microsoft Compatibility Appraiser."""
    def __init__(self):
        super().__init__(
            tweak_id="task_compat_appraiser",
            name="Tắt tác vụ Compatibility Appraiser trong Task Scheduler",
            category="Dịch Vụ Hệ Thống",
            description="Ngăn Windows chạy quét toàn bộ ổ cứng để đánh giá tương thích ứng dụng mỗi khi mở máy.",
            explanation=(
                "Tác vụ 'Microsoft Compatibility Appraiser' chạy định kỳ gây hiện tượng 100% Disk Usage\n"
                "trong 5-10 phút đầu sau khi khởi động máy. Vô hiệu hóa tác vụ này giúp máy khởi động nhanh\n"
                "và giảm tối đa độ giật lag ban đầu."
            ),
            is_recommended=True
        )
        self.task_path = r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser"

    def check(self) -> bool:
        try:
            cmd = ["schtasks.exe", "/Query", "/TN", self.task_path]
            res = run_cmd(cmd, timeout=5)
            if res.returncode == 0:
                return "Disabled" in res.stdout
            return False
        except Exception:
            return False

    def apply(self) -> Tuple[bool, str]:
        try:
            cmd = ["schtasks.exe", "/Change", "/TN", self.task_path, "/Disable"]
            res = run_cmd(cmd, timeout=10)
            if res.returncode == 0:
                return True, "Đã vô hiệu hóa Compatibility Appraiser Task thành công."
            return False, res.stderr.strip() or res.stdout.strip()
        except Exception as e:
            return False, str(e)

    def revert(self) -> Tuple[bool, str]:
        try:
            cmd = ["schtasks.exe", "/Change", "/TN", self.task_path, "/Enable"]
            res = run_cmd(cmd, timeout=10)
            if res.returncode == 0:
                return True, "Đã bật lại Compatibility Appraiser Task."
            return False, res.stderr.strip() or res.stdout.strip()
        except Exception as e:
            return False, str(e)


class DisableWerSvcTweak(ServiceTweak):
    """Tắt dịch vụ Windows Error Reporting Service (WerSvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_wersvc",
            name="Tắt dịch vụ Báo cáo sự cố Windows (WerSvc)",
            service_name="WerSvc",
            description="Ngăn Windows thu thập và truyền tệp dump chẩn đoán lỗi ngầm mỗi khi ứng dụng gặp ngoại lệ.",
            explanation=(
                "Dịch vụ 'WerSvc' chịu trách nhiệm ghi tệp crash dump và gửi báo cáo về Microsoft.\n"
                "Khi chơi game nặng hoặc game thi đấu (như Valorant), tiến trình này xử lý ngầm có thể gây khựng khung hình (hitching).\n"
                "Tắt dịch vụ này an toàn 100%, không ảnh hưởng đến bất kỳ driver phần cứng hay hệ điều hành nào."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableGeolocationTweak(ServiceTweak):
    """Tắt dịch vụ Geolocation Service (lfsvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_lfsvc",
            name="Tắt dịch vụ Định vị địa lý ngầm (Geolocation)",
            service_name="lfsvc",
            description="Vô hiệu hóa việc quét Wi-Fi liên tục để theo dõi tọa độ máy tính trong nền.",
            explanation=(
                "Dịch vụ 'lfsvc' liên tục quét và thăm dò các điểm phát Wi-Fi lân cận để xác định vị trí máy tính.\n"
                "Việc quét ngầm liên tục này dễ gây giật ping (ping spike) đột ngột khi chơi game online và làm hao pin Laptop.\n"
                "An toàn tuyệt đối cho cả PC và Laptop; không ảnh hưởng đến kết nối Internet, Wi-Fi hay Bluetooth."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableSmartCardTweak(ServiceTweak):
    """Tắt dịch vụ Smart Card (SCardSvr)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_scardsvr",
            name="Tắt dịch vụ Thẻ thông minh vật lý (SCardSvr)",
            service_name="SCardSvr",
            description="Quản lý việc kết nối đầu đọc thẻ chip thông minh vật lý (Smart Card Reader).",
            explanation=(
                "Dịch vụ 'SCardSvr' chỉ dùng cho đầu đọc thẻ chip thông minh vật lý của ngân hàng hoặc thẻ bảo mật doanh nghiệp.\n"
                "Máy tính cá nhân của game thủ và người dùng thông thường hoàn toàn không cần đến dịch vụ này.\n"
                "An toàn 100%, không bao giờ gây lỗi màn hình xanh (BSOD)."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableParentalControlsTweak(ServiceTweak):
    """Tắt dịch vụ Parental Controls (WpcMonSvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_wpc_mon",
            name="Tắt dịch vụ Giám sát Phụ huynh (Parental Controls)",
            service_name="WpcMonSvc",
            description="Vô hiệu hóa tính năng giới hạn thời gian mở máy và theo dõi ứng dụng của phụ huynh.",
            explanation=(
                "Dịch vụ 'WpcMonSvc' theo dõi thời gian mở ứng dụng và nhật ký hoạt động.\n"
                "Với người dùng máy tính cá nhân hoặc game thủ, tiến trình giám sát này chạy ngầm gây hao phí CPU không đáng có.\n"
                "Tắt dịch vụ này an toàn tuyệt đối và giúp hệ thống hoạt động tự do, nhẹ nhàng hơn."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableSharedAccessTweak(ServiceTweak):
    """Tắt dịch vụ Internet Connection Sharing (SharedAccess)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_shared_access",
            name="Tắt dịch vụ Chia sẻ mạng qua dây (ICS - SharedAccess)",
            service_name="SharedAccess",
            description="Dịch vụ biến máy tính thành bộ định tuyến chia sẻ Internet cho thiết bị khác qua dây cáp.",
            explanation=(
                "Dịch vụ 'SharedAccess' dùng để chia sẻ kết nối mạng cho máy khác qua cáp Ethernet.\n"
                "Nếu bạn kết nối trực tiếp vào Router/Wi-Fi mà không cấp mạng trung gian cho máy tính khác, tính năng này hoàn toàn dư thừa.\n"
                "Tắt dịch vụ này giúp giảm gánh nặng ngăn xếp mạng mà không ảnh hưởng đến tốc độ duyệt web hay chơi game."
            ),
            default_start_type="demand",
            is_recommended=True
        )


def get_services_tweaks() -> list[Tweak]:
    """Trả về danh sách tất cả các tùy chọn tối ưu Dịch vụ an toàn tuyệt đối (chống BSOD 100%)."""
    return [
        DisableDiagTrackTweak(),
        DisableWapPushTweak(),
        DisableWerSvcTweak(),
        DisableGeolocationTweak(),
        DisableRetailDemoTweak(),
        DisableRemoteRegistryTweak(),
        DisableMapsBrokerTweak(),
        DisableSmartCardTweak(),
        DisableParentalControlsTweak(),
        DisableSharedAccessTweak(),
        DisableCompatibilityAppraiserTweak()
    ]
