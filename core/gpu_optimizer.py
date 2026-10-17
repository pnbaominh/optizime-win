"""
Module: core/gpu_optimizer.py
Description: Triển khai GpuOptimizerService cung cấp 5 kỹ thuật tối ưu hóa GPU chuyên sâu:
             1. HAGS (Hardware Accelerated GPU Scheduling)
             2. Variable Refresh Rate (VRR)
             3. Windows Game Mode Registry Tuning
             4. GPU Priority & DWM Latency Reduction (OverlayTestMode)
             5. High Performance GPU Preference
             Tuyệt đối tuân thủ Zero-Disk Constraint: Chỉ tối ưu GPU, không can thiệp ổ đĩa.
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
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows\\Dwm",
                value_name="OverlayTestMode",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=5,  # Giảm độ trễ hàng đợi kết xuất DWM composition
                default_value=0
            ),
        )

        desc_list = [
            TweakDescriptor(
                tweak_id="gpu_hags",
                category=TweakCategory.GPU,
                title="Lập Lịch Tăng Tốc Phần Cứng GPU (HAGS)",
                description="Cho phép GPU trực tiếp quản lý VRAM mà không thông qua CPU trung gian, giảm độ trễ dựng hình và tăng FPS.",
                requires_admin=True,
                requires_reboot=True,
                registry_targets=specs_hags
            ),
            TweakDescriptor(
                tweak_id="gpu_vrr",
                category=TweakCategory.GPU,
                title="Tối Ưu Tần Số Quét Biến Thiên (Variable Refresh Rate)",
                description="Kích hoạt VRROptimizeEnable trong DirectX để hỗ trợ G-Sync/FreeSync mượt mà hơn cho các tựa game không hỗ trợ sẵn.",
                requires_admin=False,
                requires_reboot=False,
                registry_targets=()
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
                title="Ưu Tiên Kết Xuất GPU & Giảm Độ Trễ DWM",
                description="Thiết lập GPU Priority = 8 trong Multimedia Games Scheduler và giảm thời gian đệm của Desktop Window Manager.",
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
        ]

        return {d.tweak_id: d for d in desc_list}

    def get_descriptors(self) -> List[TweakDescriptor]:
        return list(self.descriptors.values())

    # -------------------------------------------------------------
    # STATUS CHECKERS
    # -------------------------------------------------------------
    def get_status(self, tweak_id: str) -> TweakState:
        with self._lock:
            if tweak_id == "gpu_vrr":
                return self._check_vrr()
            elif tweak_id == "gpu_high_performance_preference":
                return self._check_high_performance_gpu()
            elif tweak_id in self.descriptors:
                return self._check_registry_tweak(self.descriptors[tweak_id])
            return TweakState.ERROR

    def get_all_status(self) -> Dict[str, TweakState]:
        with self._lock:
            return {tid: self.get_status(tid) for tid in self.descriptors}

    def _check_vrr(self) -> TweakState:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\DirectX\UserGpuPreferences",
                0,
                winreg.KEY_READ
            ) as key:
                val, _ = winreg.QueryValueEx(key, "DirectXUserGlobalSettings")
                if "VRROptimizeEnable=1" in str(val):
                    return TweakState.OPTIMIZED
        except (FileNotFoundError, OSError):
            pass
        return TweakState.DEFAULT

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
                if tweak_id == "gpu_vrr":
                    return self._apply_vrr()
                elif tweak_id == "gpu_high_performance_preference":
                    return self._apply_high_performance_gpu(create_snapshot=create_snapshot)
                else:
                    return self._apply_registry_tweak(desc, snapshot_id)
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
                if tweak_id == "gpu_vrr":
                    return self._revert_vrr()
                elif tweak_id == "gpu_high_performance_preference":
                    return self._revert_high_performance_gpu()
                else:
                    return self._revert_registry_tweak(desc)
            except Exception as e:
                return TweakExecutionResult(
                    tweak_id=tweak_id,
                    success=False,
                    new_state=TweakState.ERROR,
                    message=f"Lỗi khi hoàn tác: {e}"
                )

    # -------------------------------------------------------------
    # SPECIFIC APPLY/REVERT IMPLEMENTATIONS
    # -------------------------------------------------------------
    def _apply_vrr(self) -> TweakExecutionResult:
        subkey = r"Software\Microsoft\DirectX\UserGpuPreferences"
        spec = RegistryTargetSpec(
            root=RegistryRoot.HKCU,
            subkey=subkey,
            value_name="DirectXUserGlobalSettings",
            value_type=RegistryValueType.REG_SZ,
            optimized_value="VRROptimizeEnable=1;",
            default_value="VRROptimizeEnable=0;"
        )
        self.backup_service.create_snapshot(TweakCategory.GPU, [spec])

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
            current_val = ""
            try:
                current_val, _ = winreg.QueryValueEx(key, "DirectXUserGlobalSettings")
            except (FileNotFoundError, OSError):
                pass

            # Giữ lại các cài đặt hiện có và chỉ update hoặc append VRROptimizeEnable=1;
            if not isinstance(current_val, str):
                current_val = str(current_val) if current_val else ""

            if "VRROptimizeEnable=" in current_val:
                new_val = re.sub(r"VRROptimizeEnable=\d+;", "VRROptimizeEnable=1;", current_val)
            else:
                new_val = (current_val.strip(";") + ";VRROptimizeEnable=1;").lstrip(";")

            winreg.SetValueEx(key, "DirectXUserGlobalSettings", 0, winreg.REG_SZ, new_val)

        return TweakExecutionResult(
            tweak_id="gpu_vrr",
            success=True,
            new_state=TweakState.OPTIMIZED,
            message="Đã kích hoạt Variable Refresh Rate (VRROptimizeEnable=1;)."
        )

    def _revert_vrr(self) -> TweakExecutionResult:
        subkey = r"Software\Microsoft\DirectX\UserGpuPreferences"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
                current_val = ""
                try:
                    current_val, _ = winreg.QueryValueEx(key, "DirectXUserGlobalSettings")
                except (FileNotFoundError, OSError):
                    pass

                if not isinstance(current_val, str):
                    current_val = str(current_val) if current_val else ""

                if "VRROptimizeEnable=" in current_val:
                    new_val = re.sub(r"VRROptimizeEnable=\d+;", "VRROptimizeEnable=0;", current_val)
                else:
                    new_val = (current_val.strip(";") + ";VRROptimizeEnable=0;").lstrip(";")

                winreg.SetValueEx(key, "DirectXUserGlobalSettings", 0, winreg.REG_SZ, new_val)
            return TweakExecutionResult(
                tweak_id="gpu_vrr",
                success=True,
                new_state=TweakState.DEFAULT,
                message="Đã khôi phục VRR về mặc định (VRROptimizeEnable=0;)."
            )
        except Exception as e:
            return TweakExecutionResult(
                tweak_id="gpu_vrr",
                success=False,
                new_state=TweakState.ERROR,
                message=f"Lỗi hoàn tác VRR: {e}"
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
