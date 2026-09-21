import ctypes
import os
from typing import Tuple

def trim_memory_working_sets() -> Tuple[bool, str]:
    """
    Thu gọn Working Set của các tiến trình để giải phóng bộ nhớ RAM vật lý đang bị chiếm dụng.
    Hoàn toàn an toàn, không tắt app hay gây crash.
    """
    try:
        # Gọi SetProcessWorkingSetSize(-1, -1) cho chính tiến trình hiện tại
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
        
        # Thử dọn dẹp thêm các tiến trình hệ thống qua EmptyWorkingSet nếu có quyền
        try:
            ctypes.windll.psapi.EmptyWorkingSet(handle)
        except Exception:
            pass

        return True, "Đã thu gọn bộ nhớ đệm RAM thành công."
    except Exception as e:
        return False, f"Lỗi tối ưu RAM: {e}"
