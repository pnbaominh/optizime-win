from typing import List, Optional, Tuple, Callable
from core.tweak_base import Tweak
from core.privacy import get_privacy_tweaks
from core.services import get_services_tweaks
from core.performance import get_performance_tweaks
from core.safety import create_system_restore_point

class OptimizerEngine:
    """Bộ điều phối trung tâm quản lý tất cả các tinh chỉnh của hệ thống."""
    def __init__(self):
        self.tweaks: List[Tweak] = []
        self.load_all_tweaks()

    def load_all_tweaks(self):
        """Nạp toàn bộ danh sách tweaks từ các module chuyên biệt."""
        self.tweaks = []
        self.tweaks.extend(get_privacy_tweaks())
        self.tweaks.extend(get_services_tweaks())
        self.tweaks.extend(get_performance_tweaks())

    def get_all_tweaks(self) -> List[Tweak]:
        return self.tweaks

    def get_tweaks_by_category(self, category: str) -> List[Tweak]:
        return [t for t in self.tweaks if t.category == category]

    def get_tweak_by_id(self, tweak_id: str) -> Optional[Tweak]:
        for t in self.tweaks:
            if t.id == tweak_id:
                return t
        return None

    def apply_tweak(self, tweak_id: str) -> Tuple[bool, str]:
        """Áp dụng 1 tinh chỉnh cụ thể theo ID."""
        tweak = self.get_tweak_by_id(tweak_id)
        if not tweak:
            return False, f"Không tìm thấy tinh chỉnh ID: {tweak_id}"
        return tweak.apply()

    def revert_tweak(self, tweak_id: str) -> Tuple[bool, str]:
        """Hoàn tác 1 tinh chỉnh cụ thể về mặc định."""
        tweak = self.get_tweak_by_id(tweak_id)
        if not tweak:
            return False, f"Không tìm thấy tinh chỉnh ID: {tweak_id}"
        return tweak.revert()

    def apply_all_recommended(self, log_callback: Optional[Callable[[str], None]] = None) -> Tuple[int, int]:
        """
        Áp dụng toàn bộ các tinh chỉnh Khuyên Dùng (An toàn 100%).
        Tự động tạo Restore Point trước khi thực hiện.
        Trả về: (Số tinh chỉnh thành công, Số tinh chỉnh thất bại).
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        log("--- BẮT ĐẦU TỐI ƯU HÓA AN TOÀN ---")
        log("[1/2] Đang tạo điểm khôi phục hệ thống (System Restore Point)...")
        sr_ok, sr_msg = create_system_restore_point("SafeOptimization")
        log(f"-> {sr_msg}")

        recommended = [t for t in self.tweaks if t.is_recommended]
        success_count = 0
        fail_count = 0

        log(f"[2/2] Đang áp dụng {len(recommended)} tinh chỉnh an toàn...")
        for tweak in recommended:
            if not tweak.check():
                ok, msg = tweak.apply()
                if ok:
                    success_count += 1
                    log(f"[+] {tweak.name}: {msg}")
                else:
                    fail_count += 1
                    log(f"[!] {tweak.name} THẤT BẠI: {msg}")
            else:
                success_count += 1
                log(f"[*] {tweak.name}: Đã ở trạng thái tối ưu từ trước.")

        log(f"--- HOÀN TẤT: {success_count} thành công, {fail_count} thất bại ---")
        return success_count, fail_count

    def revert_all(self, log_callback: Optional[Callable[[str], None]] = None) -> Tuple[int, int]:
        """
        Hoàn tác toàn bộ các tinh chỉnh đang kích hoạt về mặc định nguyên bản của Windows.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        log("--- BẮT ĐẦU HOÀN TÁC TOÀN BỘ VỀ MẶC ĐỊNH WINDOWS ---")
        success_count = 0
        fail_count = 0

        for tweak in self.tweaks:
            if tweak.check():
                ok, msg = tweak.revert()
                if ok:
                    success_count += 1
                    log(f"[+] Hoàn tác {tweak.name}: {msg}")
                else:
                    fail_count += 1
                    log(f"[!] Lỗi khi hoàn tác {tweak.name}: {msg}")

        log(f"--- HOÀN TÁC XONG: {success_count} thành công, {fail_count} thất bại ---")
        return success_count, fail_count
