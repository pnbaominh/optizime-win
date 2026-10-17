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
    """Tắt Scheduled Task Microsoft Compatibility Appraiser và chính sách chẩn đoán tương thích."""
    def __init__(self):
        super().__init__(
            tweak_id="task_compat_appraiser",
            name="Tắt tác vụ Compatibility Appraiser trong Task Scheduler",
            category="Dịch Vụ Hệ Thống",
            description="Ngăn Windows chạy quét toàn bộ ổ cứng để đánh giá tương thích ứng dụng mỗi khi mở máy.",
            explanation=(
                "Tác vụ 'Microsoft Compatibility Appraiser' chạy định kỳ gây hiện tượng 100% Disk/CPU Usage\n"
                "trong 5-10 phút đầu sau khi khởi động máy. Vô hiệu hóa tác vụ này và thiết lập Group Policy ngăn chặn\n"
                "giúp máy khởi động nhanh, ổn định và giảm tối đa độ giật lag ban đầu mà không bao giờ gặp lỗi phân quyền."
            ),
            is_recommended=True
        )
        self.task_paths = [
            r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser Exp",
            r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
            r"\Microsoft\Windows\Application Experience\ProgramDataUpdater"
        ]

    def check(self) -> bool:
        # 1. Kiểm tra chính sách Registry
        try:
            sub_key = r"SOFTWARE\Policies\Microsoft\Windows\AppCompat"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                val, _ = winreg.QueryValueEx(key, "DisableInventory")
                if val == 1:
                    return True
        except Exception:
            pass

        # 2. Kiểm tra Task Scheduler
        for tp in self.task_paths:
            try:
                cmd = ["schtasks.exe", "/Query", "/TN", tp]
                res = run_cmd(cmd, timeout=5)
                if res.returncode == 0 and "Disabled" in res.stdout:
                    return True
            except Exception:
                pass
        return False

    def apply(self) -> Tuple[bool, str]:
        reg_ok = False
        # 1. Ghi chính sách Registry Group Policy (chuẩn Microsoft để chặn CompatTelRunner.exe)
        try:
            sub_key_app = r"SOFTWARE\Policies\Microsoft\Windows\AppCompat"
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_key_app, 0, winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, "DisableInventory", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "AITEnable", 0, winreg.REG_DWORD, 0)
            
            sub_key_dc = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_key_dc, 0, winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, "AllowTelemetry", 0, winreg.REG_DWORD, 0)
            reg_ok = True
        except Exception:
            reg_ok = False

        # 2. Thử vô hiệu hóa tác vụ trong Task Scheduler (nếu hệ thống cho phép)
        for tp in self.task_paths:
            try:
                run_cmd(["schtasks.exe", "/Change", "/TN", tp, "/Disable"], timeout=5)
            except Exception:
                pass

        if reg_ok:
            return True, "Đã vô hiệu hóa Compatibility Appraiser thành công qua Group Policy và Task Scheduler."
        return False, "Không thể ghi khóa chính sách Registry (Yêu cầu quyền Administrator)."

    def revert(self) -> Tuple[bool, str]:
        # 1. Khôi phục Registry Policies
        try:
            sub_key_app = r"SOFTWARE\Policies\Microsoft\Windows\AppCompat"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key_app, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, "DisableInventory", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "AITEnable", 0, winreg.REG_DWORD, 1)
        except Exception:
            pass

        # 2. Thử bật lại tác vụ Task Scheduler
        for tp in self.task_paths:
            try:
                run_cmd(["schtasks.exe", "/Change", "/TN", tp, "/Enable"], timeout=5)
            except Exception:
                pass

        return True, "Đã khôi phục cài đặt mặc định cho Compatibility Appraiser."


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


class DisableSensorServiceTweak(ServiceTweak):
    """Tắt dịch vụ Sensor Monitoring Service (SensorService)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_sensorservice",
            name="Tắt dịch vụ Cảm biến xoay màn hình (SensorService)",
            service_name="SensorService",
            description="Vô hiệu hóa dịch vụ quản trị cảm biến xoay và cảm biến ánh sáng màn hình tablet/Surface trên PC và Laptop.",
            explanation=(
                "Dịch vụ 'SensorService' theo dõi cảm biến gia tốc, con quay hồi chuyển và độ sáng môi trường trên các thiết bị cảm ứng Surface/tablet 2-in-1.\n"
                "Trên máy tính để bàn (PC) và laptop gaming thông thường, dịch vụ này chạy ngầm là hoàn toàn thừa thãi.\n"
                "Tắt dịch vụ này giúp giảm tiến trình ngầm, an toàn 100% không ảnh hưởng đến màn hình hay driver card đồ họa."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableRemoteAccessTweak(ServiceTweak):
    """Tắt dịch vụ Routing and Remote Access (RemoteAccess)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_remoteaccess",
            name="Tắt dịch vụ Định tuyến & Truy cập từ xa (RemoteAccess - RRAS)",
            service_name="RemoteAccess",
            description="Vô hiệu hóa dịch vụ định tuyến quay số modem VPN cổ điển và NAT doanh nghiệp.",
            explanation=(
                "Dịch vụ 'RemoteAccess' (Routing and Remote Access) cung cấp các dịch vụ định tuyến cho doanh nghiệp trong môi trường mạng cục bộ hoặc diện rộng.\n"
                "Đối với người dùng máy tính cá nhân hoặc game thủ kết nối Internet qua Router/Wi-Fi thông thường, tính năng này hoàn toàn không cần thiết.\n"
                "Tắt dịch vụ giúp giảm diện tích tấn công mạng và tiết kiệm RAM/CPU, an toàn tuyệt đối 100%."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableWisvcTweak(ServiceTweak):
    """Tắt dịch vụ Windows Insider Service (wisvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_wisvc",
            name="Tắt dịch vụ Windows Insider Program (wisvc)",
            service_name="wisvc",
            description="Ngăn hệ thống ngầm kiểm tra và kết nối máy chủ gửi bản build thử nghiệm của Microsoft.",
            explanation=(
                "Dịch vụ 'wisvc' cung cấp cơ sở hạ tầng cho chương trình thử nghiệm Windows Insider Program.\n"
                "Nếu bạn sử dụng phiên bản Windows chính thức ổn định và không muốn tham gia thử nghiệm các bản vá lỗi chưa hoàn thiện, dịch vụ này chạy ngầm là không cần thiết.\n"
                "Tắt dịch vụ này giúp giảm thiểu việc kết nối máy chủ ngầm và an toàn 100%."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisablePhoneSvcTweak(ServiceTweak):
    """Tắt dịch vụ Phone Service (PhoneSvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_phone",
            name="Tắt dịch vụ Điện thoại di động (Phone Service - PhoneSvc)",
            service_name="PhoneSvc",
            description="Vô hiệu hóa tiến trình quản lý trạng thái điện thoại di động và dịch vụ viễn thông trên PC.",
            explanation=(
                "Dịch vụ 'PhoneSvc' quản lý trạng thái điện thoại di động trên thiết bị (chỉ thực sự có ý nghĩa trên thiết bị có khe SIM hoặc modem di động).\n"
                "Trên máy tính để bàn (PC) và laptop thông thường, tiến trình này hoàn toàn thừa thãi.\n"
                "Tắt dịch vụ an toàn 100%, không ảnh hưởng đến Wi-Fi, Ethernet, Bluetooth hay mạng Internet."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableSEMgrSvcTweak(ServiceTweak):
    """Tắt dịch vụ Payments and NFC/SE Manager (SEMgrSvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_semgrsvc",
            name="Tắt dịch vụ Quản lý thanh toán chip NFC (SEMgrSvc)",
            service_name="SEMgrSvc",
            description="Dịch vụ quản lý phần tử bảo mật thanh toán chạm qua chip NFC phần cứng.",
            explanation=(
                "Dịch vụ 'SEMgrSvc' (Payments and NFC/SE Manager) dùng để quản lý giao dịch thanh toán quẹt thẻ qua chip NFC trên thiết bị phần cứng hỗ trợ.\n"
                "Các dòng PC và Laptop cá nhân không sử dụng tính năng này để chạm thanh toán.\n"
                "Tắt dịch vụ giúp giảm thiểu tiến trình nền không cần thiết, an toàn 100%."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableWalletServiceTweak(ServiceTweak):
    """Tắt dịch vụ Microsoft Wallet (WalletService)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_wallet",
            name="Tắt dịch vụ Ví điện tử Microsoft Wallet (WalletService)",
            service_name="WalletService",
            description="Vô hiệu hóa dịch vụ lưu trữ thẻ thanh toán của ứng dụng Microsoft Wallet.",
            explanation=(
                "Dịch vụ 'WalletService' hỗ trợ lưu trữ thẻ tín dụng và vé số cho ứng dụng Microsoft Wallet.\n"
                "Người dùng thông thường và game thủ thực hiện thanh toán trực tiếp qua trình duyệt web an toàn (Steam, Riot, Momo, thẻ ngân hàng, v.v.).\n"
                "Tắt dịch vụ này giúp giảm bớt tài nguyên ngầm và an toàn 100%."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableScDeviceEnumTweak(ServiceTweak):
    """Tắt dịch vụ Smart Card Device Enumeration (ScDeviceEnum)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_sc_device_enum",
            name="Tắt dịch vụ Liệt kê đầu đọc thẻ chip thông minh (ScDeviceEnum)",
            service_name="ScDeviceEnum",
            description="Ngăn hệ thống định kỳ tạo các nút thiết bị phần mềm tìm kiếm đầu đọc thẻ chip thông minh.",
            explanation=(
                "Dịch vụ 'ScDeviceEnum' chịu trách nhiệm tạo và giám sát các nút thiết bị phần mềm cho đầu đọc Smart Card vật lý.\n"
                "Khi máy tính không cắm đầu đọc thẻ chip bảo mật văn phòng, dịch vụ này chạy ngầm là hoàn toàn dư thừa.\n"
                "An toàn tuyệt đối 100%, không bao giờ gây lỗi màn hình xanh (BSOD)."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableSCPolicySvcTweak(ServiceTweak):
    """Tắt chính sách Smart Card Removal Policy (SCPolicySvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_sc_policy",
            name="Tắt chính sách Khóa máy khi rút thẻ chip (SCPolicySvc)",
            service_name="SCPolicySvc",
            description="Vô hiệu hóa dịch vụ cấu hình khóa desktop khi rút thẻ thông minh vật lý.",
            explanation=(
                "Dịch vụ 'SCPolicySvc' (Smart Card Removal Policy) chỉ dùng trong các cơ quan chính phủ hoặc ngân hàng yêu cầu rút thẻ chip là khóa máy tính.\n"
                "Người dùng cá nhân khóa máy tính thủ công bằng tổ hợp phím Windows + L.\n"
                "Tắt dịch vụ này giúp hệ thống gọn nhẹ, an toàn 100%."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableLltdsvcTweak(ServiceTweak):
    """Tắt dịch vụ Link-Layer Topology Discovery Mapper (lltdsvc)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_lltdsvc",
            name="Tắt dịch vụ Thăm dò sơ đồ mạng cục bộ cũ (lltdsvc - LLTD)",
            service_name="lltdsvc",
            description="Ngăn chặn việc gửi các gói tin thăm dò vẽ sơ đồ thiết bị mạng LAN theo chuẩn cũ.",
            explanation=(
                "Dịch vụ 'lltdsvc' (Link-Layer Topology Discovery Mapper) tạo bản đồ mạng hiển thị vị trí các thiết bị từ thời Windows Vista.\n"
                "Các ứng dụng hiện đại không còn sử dụng giao thức này; việc thăm dò ngầm liên tục chỉ làm tiêu tốn băng thông và chu kỳ CPU.\n"
                "Tắt dịch vụ này hoàn toàn không làm gián đoạn kết nối Internet hay mạng nội bộ LAN/Wi-Fi."
            ),
            default_start_type="demand",
            is_recommended=True
        )


class DisableNetTcpPortSharingTweak(ServiceTweak):
    """Tắt dịch vụ Net.Tcp Port Sharing (NetTcpPortSharing)."""
    def __init__(self):
        super().__init__(
            tweak_id="service_nettcpportsharing",
            name="Tắt dịch vụ Chia sẻ cổng Net.Tcp (.NET Framework WCF)",
            service_name="NetTcpPortSharing",
            description="Vô hiệu hóa dịch vụ chia sẻ cổng TCP cho các giao thức mạng WCF doanh nghiệp cũ.",
            explanation=(
                "Dịch vụ 'NetTcpPortSharing' cho phép nhiều tiến trình dịch vụ chia sẻ cùng một cổng TCP qua giao thức net.tcp.\n"
                "Tính năng này chỉ phục vụ các hệ thống máy chủ doanh nghiệp phát triển trên WCF cũ, không có game hay phần mềm tiêu dùng nào cần tới.\n"
                "Tắt dịch vụ giúp giảm diện tích tấn công mạng (attack surface) và an toàn tuyệt đối 100%."
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
        DisableCompatibilityAppraiserTweak(),
        DisableSensorServiceTweak(),
        DisableRemoteAccessTweak(),
        DisableWisvcTweak(),
        DisablePhoneSvcTweak(),
        DisableSEMgrSvcTweak(),
        DisableWalletServiceTweak(),
        DisableScDeviceEnumTweak(),
        DisableSCPolicySvcTweak(),
        DisableLltdsvcTweak(),
        DisableNetTcpPortSharingTweak()
    ]
