"""
Module: core/gpu_optimizer.py
Description: Triển khai GpuOptimizerService cung cấp 5 kỹ thuật tối ưu hóa GPU chuyên sâu & an toàn cho Esports/Valorant:
             1. HAGS (Hardware Accelerated GPU Scheduling)
             2. Disable GameDVR & Optimize Fullscreen Exclusive (Chống giật & drop FPS)
             3. Windows Game Mode Registry Tuning
             4. GPU Priority Scheduling (Safe MPO - không gây lỗi nhấp nháy đen màn hình trên Optimus Laptop)
             5. High Performance GPU Preference (GpuPreference=2)
             Tuyệt đối tuân thủ Zero-Disk Constraint: Chỉ tối ưu GPU/Render, không can thiệp ổ đĩa.
"""

from __future__ import annotations
import ctypes
import re
import threading
import winreg
from typing import Dict, List, Optional, Tuple

from core.contracts import (
    TweakCategory,
    TweakState,
    RegistryRoot,
    RegistryValueType,
    RegistryTargetSpec,
    TweakDescriptor,
    TweakExecutionResult,
)
from core.registry_backup import RegistryBackupService


class GpuOptimizerService:
    """Dịch vụ tối ưu hóa bộ xử lý đồ họa (GPU) chuyên sâu."""

    def __init__(self, backup_service: Optional[RegistryBackupService] = None):
        self.backup_service = backup_service or RegistryBackupService()
        self._lock = threading.RLock()
        self._saved_gpu_pref: Optional[RegistryBackupEntry] = None
        self.descriptors: Dict[str, TweakDescriptor] = self._init_descriptors()
        self.clean_legacy_dangerous_tweaks()

    @staticmethod
    def clean_legacy_dangerous_tweaks() -> None:
        """Dọn dẹp các thiết lập cũ nguy hiểm gây nhấp nháy đen hoặc khựng màn hình trên laptop Optimus:
        1. Xóa OverlayTestMode trong HKLM\\SOFTWARE\\Microsoft\\Windows\\Dwm (khôi phục MPO).
        2. Tắt VRROptimizeEnable trong HKCU\\Software\\Microsoft\\DirectX\\UserGpuPreferences.
        """
        # 1. Clean OverlayTestMode (khôi phục Multi-Plane Overlay)
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\Dwm",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
            ) as key:
                winreg.DeleteValue(key, "OverlayTestMode")
        except Exception:
            pass

        # 2. Clean VRROptimizeEnable (khôi phục đồng bộ tần số quét)
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\DirectX\UserGpuPreferences",
                0,
                winreg.KEY_READ | winreg.KEY_SET_VALUE
            ) as key:
                val, _ = winreg.QueryValueEx(key, "DirectXUserGlobalSettings")
                if isinstance(val, str) and "VRROptimizeEnable=1;" in val:
                    new_val = val.replace("VRROptimizeEnable=1;", "")
                    winreg.SetValueEx(key, "DirectXUserGlobalSettings", 0, winreg.REG_SZ, new_val)
        except Exception:
            pass

    def is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _init_descriptors(self) -> Dict[str, TweakDescriptor]:
        specs_hags = (
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
                value_name="HwSchMode",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=2,  # 2 = Bật Hardware Accelerated GPU Scheduling
                default_value=1
            ),
        )

        specs_game_mode = (
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="Software\\Microsoft\\GameBar",
                value_name="AllowAutoGameMode",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=1,
                default_value=0
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="Software\\Microsoft\\GameBar",
                value_name="AutoGameModeEnabled",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=1,
                default_value=0
            ),
        )

        specs_priority = (
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games",
                value_name="GPU Priority",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=8,  # Tối đa hóa phân bổ luồng GPU cho Games
                default_value=2
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games",
                value_name="Priority",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=6,
                default_value=2
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games",
                value_name="Scheduling Category",
                value_type=RegistryValueType.REG_SZ,
                optimized_value="High",
                default_value="Medium"
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games",
                value_name="SFIO Priority",
                value_type=RegistryValueType.REG_SZ,
                optimized_value="High",
                default_value="Normal"
            ),
        )

        specs_gamedvr = (
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="System\\GameConfigStore",
                value_name="GameDVR_Enabled",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=0,
                default_value=1
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="System\\GameConfigStore",
                value_name="GameDVR_FSEBehaviorMode",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=2,
                default_value=0
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="System\\GameConfigStore",
                value_name="GameDVR_HonorUserFSEBehaviorMode",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=1,
                default_value=0
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="System\\GameConfigStore",
                value_name="GameDVR_DXGIHonorFSEWindowsCompatible",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=1,
                default_value=0
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
                value_name="AppCaptureEnabled",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=0,
                default_value=1
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey="Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
                value_name="HistoricalCaptureEnabled",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=0,
                default_value=1
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Policies\\Microsoft\\Windows\\GameDVR",
                value_name="AllowGameDVR",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=0,
                default_value=1
            ),
        )

        specs_tdr = (
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
                value_name="TdrDelay",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=8,  # Chờ 8 giây trước khi reset GPU, chống văng game/nháy đen
                default_value=2
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
                value_name="TdrDdiDelay",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=8,
                default_value=5
            ),
        )

        specs_directx_affinity = (
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games",
                value_name="Clock Rate",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=10000,
                default_value=2710
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games",
                value_name="Affinity",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=0,  # Giải phóng luồng đồ họa trên toàn bộ nhân CPU, không dồn Core 0
                default_value=0
            ),
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games",
                value_name="Background Only",
                value_type=RegistryValueType.REG_SZ,
                optimized_value="False",
                default_value="False"
            ),
        )

        desc_list = [
            TweakDescriptor(
                tweak_id="gpu_hags",
                category=TweakCategory.GPU,
                title="Lập Lịch Tăng Tốc Phần Cứng GPU (HAGS)",
                description="Cho phép GPU trực tiếp quản lý VRAM. (Khuyến nghị: Nếu chơi Valorant bị khựng chuột hoặc crash Vanguard trên laptop Optimus, hãy để Tắt).",
                requires_admin=True,
                requires_reboot=True,
                registry_targets=specs_hags
            ),
            TweakDescriptor(
                tweak_id="gpu_disable_gamedvr",
                category=TweakCategory.GPU,
                title="Tắt Windows GameDVR & Ép True Fullscreen (Chống Giật & Xé Hình)",
                description="Vô hiệu hóa tính năng quay video ngầm (GameDVR, AppCapture) của Windows và tối ưu chế độ FSE, loại bỏ giật lag, nhấp nháy đen và drop FPS khi chơi Valorant.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=specs_gamedvr
            ),
            TweakDescriptor(
                tweak_id="gpu_game_mode",
                category=TweakCategory.GPU,
                title="Kích Hoạt Chế Độ Windows Game Mode Chuyên Sâu",
                description="Ưu tiên toàn bộ tài nguyên luồng render GPU và ngăn chặn cập nhật chạy ngầm khi trò chơi đang hoạt động.",
                requires_admin=False,
                requires_reboot=False,
                registry_targets=specs_game_mode
            ),
            TweakDescriptor(
                tweak_id="gpu_priority_dwm_flush",
                category=TweakCategory.GPU,
                title="Ưu Tiên Lập Lịch Luồng GPU & Giảm Input Lag (Safe MPO)",
                description="Thiết lập GPU Priority = 8, Priority = 6, SFIO Priority = High trong Multimedia SystemProfile cho Games mà không can thiệp MPO, bảo đảm an toàn 100% cho màn hình và laptop Optimus.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=specs_priority
            ),
            TweakDescriptor(
                tweak_id="gpu_high_performance_preference",
                category=TweakCategory.GPU,
                title="Ưu Tiên Card Đồ Họa Rời Hiệu Năng Cao (GpuPreference=2)",
                description="Cấu hình hệ thống DirectX luôn chỉ định GPU rời (Discrete GPU) xử lý các ứng dụng đồ họa nặng.",
                requires_admin=False,
                requires_reboot=False,
                registry_targets=()
            ),
            TweakDescriptor(
                tweak_id="gpu_tdr_delay",
                category=TweakCategory.GPU,
                title="Chống Văng Game & Phục Hồi Driver Đồ Họa (TdrDelay 8s)",
                description="Nâng ngưỡng chờ phản hồi GPU từ 2 giây lên 8 giây theo chuẩn Microsoft, chống crash game và chống nháy đen màn hình khi tải nặng hoặc Alt-Tab.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=specs_tdr
            ),
            TweakDescriptor(
                tweak_id="gpu_directx_thread_affinity",
                category=TweakCategory.GPU,
                title="Tối Ưu Lập Lịch Luồng Đồ Họa DirectX (Game Clock Rate & Affinity)",
                description="Thiết lập xung nhịp lấy mẫu 10000 và Affinity = 0, giải phóng luồng render DirectX trên toàn bộ nhân CPU thay vì dồn vào Core 0.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=specs_directx_affinity
            ),
        ]

        return {d.tweak_id: d for d in desc_list}

    def get_descriptors(self) -> List[TweakDescriptor]:
        return list(self.descriptors.values())

    # -------------------------------------------------------------
    # STATUS CHECKERS
    # -------------------------------------------------------------
    def get_status(self, tweak_id: str) -> TweakState:
        with self._lock:
            if tweak_id == "gpu_high_performance_preference":
                return self._check_high_performance_gpu()
            elif tweak_id in self.descriptors:
                return self._check_registry_tweak(self.descriptors[tweak_id])
            return TweakState.ERROR

    def get_all_status(self) -> Dict[str, TweakState]:
        with self._lock:
            return {tid: self.get_status(tid) for tid in self.descriptors}

    def _check_high_performance_gpu(self) -> TweakState:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\DirectX\UserGpuPreferences",
                0,
                winreg.KEY_READ
            ) as key:
                val, _ = winreg.QueryValueEx(key, "DefaultGpuPreference")
                if val == 2:
                    return TweakState.OPTIMIZED
        except (FileNotFoundError, OSError):
            pass
        return TweakState.DEFAULT

    def _check_registry_tweak(self, descriptor: TweakDescriptor) -> TweakState:
        if not descriptor.registry_targets:
            return TweakState.DEFAULT

        all_optimized = True
        for target in descriptor.registry_targets:
            hroot = winreg.HKEY_LOCAL_MACHINE if target.root == RegistryRoot.HKLM else winreg.HKEY_CURRENT_USER
            access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            try:
                with winreg.OpenKey(hroot, target.subkey, 0, access) as key:
                    val, _ = winreg.QueryValueEx(key, target.value_name)
                    if val != target.optimized_value:
                        all_optimized = False
                        break
            except (FileNotFoundError, OSError):
                all_optimized = False
                break

        return TweakState.OPTIMIZED if all_optimized else TweakState.DEFAULT

    # -------------------------------------------------------------
    # APPLY & REVERT LOGIC
    # -------------------------------------------------------------
    def apply_tweak(self, tweak_id: str, create_snapshot: bool = True) -> TweakExecutionResult:
        with self._lock:
            if tweak_id not in self.descriptors:
                return TweakExecutionResult(
                    tweak_id=tweak_id,
                    success=False,
                    new_state=TweakState.ERROR,
                    message=f"Tweak '{tweak_id}' không tồn tại."
                )

            desc = self.descriptors[tweak_id]
            if desc.requires_admin and not self.is_admin():
                return TweakExecutionResult(
                    tweak_id=tweak_id,
                    success=False,
                    new_state=TweakState.ERROR,
                    message="Thao tác yêu cầu quyền Quản trị viên (Run as Administrator)."
                )

            snapshot_id = None
            if create_snapshot and desc.registry_targets:
                snapshot = self.backup_service.create_snapshot(
                    category=TweakCategory.GPU,
                    targets=list(desc.registry_targets)
                )
                snapshot_id = snapshot.snapshot_id

            try:
                if tweak_id == "gpu_high_performance_preference":
                    return self._apply_high_performance_gpu(create_snapshot=create_snapshot)
                else:
                    res = self._apply_registry_tweak(desc, snapshot_id)
                    if tweak_id in ("gpu_priority_dwm_flush", "gpu_disable_gamedvr"):
                        self.clean_legacy_dangerous_tweaks()
                    return res
            except Exception as e:
                return TweakExecutionResult(
                    tweak_id=tweak_id,
                    success=False,
                    new_state=TweakState.ERROR,
                    message=f"Lỗi khi áp dụng: {e}",
                    snapshot_id=snapshot_id
                )

    def revert_tweak(self, tweak_id: str) -> TweakExecutionResult:
        with self._lock:
            if tweak_id not in self.descriptors:
                return TweakExecutionResult(
                    tweak_id=tweak_id,
                    success=False,
                    new_state=TweakState.ERROR,
                    message=f"Tweak '{tweak_id}' không tồn tại."
                )

            desc = self.descriptors[tweak_id]
            if desc.requires_admin and not self.is_admin():
                return TweakExecutionResult(
                    tweak_id=tweak_id,
                    success=False,
                    new_state=TweakState.ERROR,
                    message="Thao tác yêu cầu quyền Quản trị viên (Run as Administrator)."
                )

            try:
                if tweak_id == "gpu_high_performance_preference":
                    return self._revert_high_performance_gpu()
                else:
                    res = self._revert_registry_tweak(desc)
                    if tweak_id in ("gpu_priority_dwm_flush", "gpu_disable_gamedvr"):
                        self.clean_legacy_dangerous_tweaks()
                    return res
            except Exception as e:
                return TweakExecutionResult(
                    tweak_id=tweak_id,
                    success=False,
                    new_state=TweakState.ERROR,
                    message=f"Lỗi khi hoàn tác: {e}"
                )

    def _apply_high_performance_gpu(self, create_snapshot: bool = True) -> TweakExecutionResult:
        subkey = r"Software\Microsoft\DirectX\UserGpuPreferences"
        # Ghi nhận trạng thái Registry ban đầu trước khi sửa
        prev_entry = self.backup_service.capture_entry(RegistryRoot.HKCU, subkey, "DefaultGpuPreference")
        self._saved_gpu_pref = prev_entry

        if create_snapshot:
            spec = RegistryTargetSpec(
                root=RegistryRoot.HKCU,
                subkey=subkey,
                value_name="DefaultGpuPreference",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=2,
                default_value=0
            )
            self.backup_service.create_snapshot(TweakCategory.GPU, [spec])

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
            winreg.SetValueEx(key, "DefaultGpuPreference", 0, winreg.REG_DWORD, 2)

        return TweakExecutionResult(
            tweak_id="gpu_high_performance_preference",
            success=True,
            new_state=TweakState.OPTIMIZED,
            message="Đã thiết lập ưu tiên GPU rời hiệu năng cao (DefaultGpuPreference = 2)."
        )

    def _revert_high_performance_gpu(self) -> TweakExecutionResult:
        subkey = r"Software\Microsoft\DirectX\UserGpuPreferences"
        try:
            prev = self._saved_gpu_pref
            if not prev:
                # Tìm trong snapshot gần nhất nếu có
                snaps = self.backup_service.list_snapshots(TweakCategory.GPU)
                for s in snaps:
                    snap_obj = self.backup_service.load_snapshot(s["snapshot_id"])
                    if snap_obj:
                        for e in snap_obj.entries:
                            if e.root == RegistryRoot.HKCU and e.value_name == "DefaultGpuPreference":
                                prev = e
                                break
                    if prev:
                        break

            if prev and prev.existed_before and prev.previous_value is not None:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
                    winreg.SetValueEx(key, "DefaultGpuPreference", 0, prev.value_type, prev.previous_value)
                msg = f"Đã khôi phục lựa chọn GPU trước đó ({prev.previous_value})."
            else:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as key:
                    try:
                        winreg.DeleteValue(key, "DefaultGpuPreference")
                    except FileNotFoundError:
                        pass
                msg = "Đã khôi phục lựa chọn GPU mặc định của Windows."

            return TweakExecutionResult(
                tweak_id="gpu_high_performance_preference",
                success=True,
                new_state=TweakState.DEFAULT,
                message=msg
            )
        except Exception as e:
            return TweakExecutionResult(
                tweak_id="gpu_high_performance_preference",
                success=False,
                new_state=TweakState.ERROR,
                message=f"Lỗi hoàn tác High Performance GPU: {e}"
            )

    def _apply_registry_tweak(self, desc: TweakDescriptor, snapshot_id: Optional[str]) -> TweakExecutionResult:
        for target in desc.registry_targets:
            hroot = winreg.HKEY_LOCAL_MACHINE if target.root == RegistryRoot.HKLM else winreg.HKEY_CURRENT_USER
            access = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
            with winreg.CreateKeyEx(hroot, target.subkey, 0, access) as key:
                winreg.SetValueEx(
                    key,
                    target.value_name,
                    0,
                    int(target.value_type),
                    target.optimized_value
                )

        msg = f"Đã áp dụng tối ưu: {desc.title}"
        if desc.requires_reboot:
            msg += " (Cần khởi động lại máy để có hiệu lực)."

        return TweakExecutionResult(
            tweak_id=desc.tweak_id,
            success=True,
            new_state=TweakState.OPTIMIZED,
            message=msg,
            requires_reboot=desc.requires_reboot,
            snapshot_id=snapshot_id
        )

    def _revert_registry_tweak(self, desc: TweakDescriptor) -> TweakExecutionResult:
        for target in desc.registry_targets:
            hroot = winreg.HKEY_LOCAL_MACHINE if target.root == RegistryRoot.HKLM else winreg.HKEY_CURRENT_USER
            access = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
            try:
                with winreg.OpenKey(hroot, target.subkey, 0, access) as key:
                    winreg.SetValueEx(
                        key,
                        target.value_name,
                        0,
                        int(target.value_type),
                        target.default_value
                    )
            except (FileNotFoundError, OSError):
                pass

        return TweakExecutionResult(
            tweak_id=desc.tweak_id,
            success=True,
            new_state=TweakState.DEFAULT,
            message=f"Đã khôi phục mặc định: {desc.title}",
            requires_reboot=desc.requires_reboot
        )

    # -------------------------------------------------------------
    # BATCH OPERATIONS
    # -------------------------------------------------------------
    def quick_apply_all(self) -> Dict[str, TweakExecutionResult]:
        with self._lock:
            all_targets = []
            for d in self.descriptors.values():
                all_targets.extend(d.registry_targets)

            self.backup_service.create_snapshot(
                category=TweakCategory.GPU,
                targets=all_targets,
                snapshot_id="gpu_quick_apply_batch"
            )

            results = {}
            for tid in self.descriptors:
                results[tid] = self.apply_tweak(tid, create_snapshot=False)
            return results

    def revert_all(self) -> Dict[str, TweakExecutionResult]:
        with self._lock:
            results = {}
            for tid in self.descriptors:
                results[tid] = self.revert_tweak(tid)
            return results
