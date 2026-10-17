"""
Module: core/ram_optimizer.py
Description: Triển khai các nâng cấp tối ưu hóa RAM chuyên sâu:
             1. DisablePagingExecutive (Giữ Windows Kernel và Driver hoàn toàn trong RAM vật lý)
             2. SvcHostSplitThresholdInKB (Gom / tách tiến trình svchost theo dung lượng RAM hệ thống)
             3. AutoStandbyPurgeWorker (Luồng nền tự động dọn Standby List khi RAM > 80%)
             Tích hợp đầy đủ cùng các API dọn dẹp RAM của core.memory_optimizer.
             Tuyệt đối tuân thủ Zero-Disk Constraint: Không can thiệp ổ đĩa.
"""

from __future__ import annotations
import ctypes
import os
import threading
import time
import winreg
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from core.contracts import RamStatusMetrics
from core.memory_optimizer import (
    get_detailed_memory_info,
    purge_standby_list,
    trim_all_working_sets,
    full_memory_purge,
    set_sysmain_boot,
    set_memory_compression_boot,
    set_large_system_cache_boot,
    get_boot_memory_status,
    enable_privilege,
    MEMORYSTATUSEX,
)
from core.registry_backup import RegistryBackupService
from core.contracts import TweakCategory, RegistryRoot, RegistryTargetSpec, RegistryValueType

# Giá trị mặc định của Windows cho SvcHostSplitThresholdInKB: 3,670,016 KB (~3.5 GB)
WINDOWS_DEFAULT_SVCHOST_SPLIT_KB = 3670016


def get_total_physical_ram_kb() -> int:
    """Lấy tổng dung lượng RAM vật lý của hệ thống tính theo Kilobytes."""
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return int(stat.ullTotalPhys // 1024)
    except Exception:
        pass
    return 8 * 1024 * 1024  # Fallback 8GB


def get_disable_paging_executive() -> bool:
    """Kiểm tra xem DisablePagingExecutive có đang bật (= 1) hay không."""
    try:
        reg_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            val, _ = winreg.QueryValueEx(k, "DisablePagingExecutive")
            return val == 1
    except (FileNotFoundError, OSError):
        return False


def set_disable_paging_executive(enable: bool, backup_service: Optional[RegistryBackupService] = None) -> Tuple[bool, str]:
    """
    Bật/tắt DisablePagingExecutive trong Windows:
    1 = Giữ toàn bộ kernel driver và mã thực thi hệ thống trong RAM vật lý (giảm độ trễ paging).
    0 = Cho phép phân trang kernel driver xuống tệp hoán đổi ảo (mặc định Windows).
    """
    reg_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
    val = 1 if enable else 0

    if backup_service:
        spec = RegistryTargetSpec(
            root=RegistryRoot.HKLM,
            subkey=reg_path,
            value_name="DisablePagingExecutive",
            value_type=RegistryValueType.REG_DWORD,
            optimized_value=1,
            default_value=0
        )
        backup_service.create_snapshot(TweakCategory.RAM, [spec])

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.SetValueEx(k, "DisablePagingExecutive", 0, winreg.REG_DWORD, val)
        if enable:
            return True, "Đã bật DisablePagingExecutive = 1 (Giữ Windows Kernel và Driver trong RAM vật lý)."
        return True, "Đã khôi phục DisablePagingExecutive về 0 (Mặc định hệ thống)."
    except Exception as e:
        return False, f"Lỗi thiết lập DisablePagingExecutive: {e}"


def get_svchost_split_status() -> Tuple[bool, int, int]:
    """
    Kiểm tra trạng thái SvcHostSplitThresholdInKB.
    Trả về: (đã tối ưu hóa theo RAM hay chưa, giá trị hiện tại theo KB, tổng RAM theo KB)
    """
    total_ram_kb = get_total_physical_ram_kb()
    current_val_kb = WINDOWS_DEFAULT_SVCHOST_SPLIT_KB
    try:
        reg_path = r"SYSTEM\CurrentControlSet\Control"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            val, _ = winreg.QueryValueEx(k, "SvcHostSplitThresholdInKB")
            current_val_kb = int(val)
    except (FileNotFoundError, OSError):
        pass

    is_optimized = (current_val_kb >= total_ram_kb)
    return is_optimized, current_val_kb, total_ram_kb


def apply_svchost_split_threshold(enable: bool, backup_service: Optional[RegistryBackupService] = None) -> Tuple[bool, str]:
    """
    Cấu hình SvcHostSplitThresholdInKB:
    Nếu enable: Gán giá trị bằng tổng dung lượng RAM vật lý tính theo KB (hoặc 1024 * 1024 * dung lượng GB).
    Nếu disable: Khôi phục về mặc định 3,670,016 KB (~3.5 GB).
    """
    reg_path = r"SYSTEM\CurrentControlSet\Control"
    total_ram_kb = get_total_physical_ram_kb()
    target_val = total_ram_kb if enable else WINDOWS_DEFAULT_SVCHOST_SPLIT_KB

    if backup_service:
        spec = RegistryTargetSpec(
            root=RegistryRoot.HKLM,
            subkey=reg_path,
            value_name="SvcHostSplitThresholdInKB",
            value_type=RegistryValueType.REG_DWORD,
            optimized_value=total_ram_kb,
            default_value=WINDOWS_DEFAULT_SVCHOST_SPLIT_KB
        )
        backup_service.create_snapshot(TweakCategory.RAM, [spec])

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.SetValueEx(k, "SvcHostSplitThresholdInKB", 0, winreg.REG_DWORD, target_val)
        if enable:
            ram_gb = round(total_ram_kb / (1024 * 1024), 1)
            return True, f"Đã tối ưu SvcHostSplitThresholdInKB = {target_val} KB ({ram_gb} GB RAM)."
        return True, f"Đã khôi phục SvcHostSplitThresholdInKB về mặc định ({WINDOWS_DEFAULT_SVCHOST_SPLIT_KB} KB)."
    except Exception as e:
        return False, f"Lỗi thiết lập SvcHostSplitThresholdInKB: {e}"


class AutoStandbyPurgeWorker:
    """
    Luồng daemon chạy nền tự động dọn dẹp Standby List và Working Sets
    khi mức sử dụng RAM hệ thống vượt quá 80%.
    Được trang bị cơ chế Cooldown (120 giây) để tránh Memory Thrashing.
    """

    def __init__(self, check_interval_sec: float = 20.0, usage_threshold_pct: float = 80.0, cooldown_sec: float = 120.0):
        self.check_interval_sec = check_interval_sec
        self.usage_threshold_pct = usage_threshold_pct
        self.cooldown_sec = cooldown_sec

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.last_purge_time: Optional[float] = None
        self.last_purge_iso: Optional[str] = None
        self.purge_count: int = 0
        self.total_freed_mb: int = 0

    def start(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="AutoStandbyPurgeWorker", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return False
            self._stop_event.set()
            self._thread.join(timeout=2.0)
            self._thread = None
            return True

    def is_running(self) -> bool:
        with self._lock:
            return bool(self._thread and self._thread.is_alive())

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                info = get_detailed_memory_info()
                pct = info.get("percent_used", 0)

                now = time.time()
                cooldown_ok = (self.last_purge_time is None) or ((now - self.last_purge_time) >= self.cooldown_sec)

                if pct >= self.usage_threshold_pct and cooldown_ok:
                    ok, msg, freed_mb = purge_standby_list()
                    if ok:
                        self.last_purge_time = now
                        self.last_purge_iso = datetime.now(timezone.utc).isoformat()
                        self.purge_count += 1
                        self.total_freed_mb += freed_mb
            except Exception:
                pass

            # Chờ đợi thông qua stop_event để phản hồi dừng tức thì
            self._stop_event.wait(self.check_interval_sec)

    def get_metrics(self) -> RamStatusMetrics:
        info = get_detailed_memory_info()
        total_kb = int(info.get("total_mb", 0) * 1024)
        avail_kb = int(info.get("avail_mb", 0) * 1024)
        pct = float(info.get("percent_used", 0.0))
        _, _, calc_svchost = get_svchost_split_status()

        return RamStatusMetrics(
            total_physical_kb=max(1, total_kb),
            available_physical_kb=max(0, avail_kb),
            usage_percent=pct,
            calculated_svchost_threshold_kb=calc_svchost,
            standby_purge_active=self.is_running(),
            last_purge_timestamp_iso=self.last_purge_iso
        )


# Singleton instance toàn cầu của AutoStandbyPurgeWorker
_global_purge_worker: Optional[AutoStandbyPurgeWorker] = None
_worker_init_lock = threading.Lock()


def get_auto_purge_worker() -> AutoStandbyPurgeWorker:
    global _global_purge_worker
    with _worker_init_lock:
        if _global_purge_worker is None:
            _global_purge_worker = AutoStandbyPurgeWorker()
        return _global_purge_worker
