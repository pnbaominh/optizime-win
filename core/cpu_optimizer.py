"""
Module: core/cpu_optimizer.py
Description: Triển khai CpuOptimizerService cung cấp 5 kỹ thuật tối ưu hóa CPU chuyên sâu:
             1. Ultimate Performance Power Plan
             2. Win32PrioritySeparation Foreground Boost
             3. CPU Core Unparking (CPMINCORES 100%)
             4. MMCSS SystemResponsiveness tweak
             5. Power Throttling Disable
             Tuyệt đối tuân thủ Zero-Disk Constraint: Chỉ tối ưu CPU, không can thiệp ổ đĩa.
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
from core.process_utils import run_cmd

# GUIDs chuẩn Windows cho Power Scheme & Processor Subgroup
ULTIMATE_PERF_BASE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"
BALANCED_SCHEME_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"
SUB_PROCESSOR_GUID = "54533251-82be-4824-96c1-47b60b740d00"
CPMINCORES_SETTING_GUID = "0cc5b647-c1df-4637-891a-dec35c318583"


class CpuOptimizerService:
    """Dịch vụ tối ưu hóa vi xử lý (CPU) chuyên sâu."""

    def __init__(self, backup_service: Optional[RegistryBackupService] = None):
        self.backup_service = backup_service or RegistryBackupService()
        self._lock = threading.RLock()
        self._saved_cpmincores: Optional[Tuple[int, int]] = None
        self.descriptors: Dict[str, TweakDescriptor] = self._init_descriptors()

    def is_admin(self) -> bool:
        """Kiểm tra quyền Administrator của tiến trình."""
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _init_descriptors(self) -> Dict[str, TweakDescriptor]:
        specs_win32 = (
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SYSTEM\\CurrentControlSet\\Control\\PriorityControl",
                value_name="Win32PrioritySeparation",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=0x26,  # 38 thập phân: ưu tiên tiền cảnh tối đa, quantum ngắn biến thiên
                default_value=0x02
            ),
        )

        specs_mmcss = (
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile",
                value_name="SystemResponsiveness",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=10,  # 10% cho background, 90% CPU cho multimedia/gaming realtime
                default_value=20
            ),
        )

        specs_throttling = (
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SYSTEM\\CurrentControlSet\\Control\\Power\\PowerThrottling",
                value_name="PowerThrottlingOff",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=1,  # Tắt power throttling để giải phóng 100% xung nhịp
                default_value=0
            ),
        )

        desc_list = [
            TweakDescriptor(
                tweak_id="cpu_ultimate_power_plan",
                category=TweakCategory.CPU,
                title="Ultimate Performance Power Plan",
                description="Kích hoạt và chuyển sang cấu hình nguồn Ultimate Performance, loại bỏ hoàn toàn độ trễ hạ xung của CPU.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=()
            ),
            TweakDescriptor(
                tweak_id="cpu_win32_priority_separation",
                category=TweakCategory.CPU,
                title="Tối Ưu Win32PrioritySeparation (Foreground Boost)",
                description="Cấu hình CPU ưu tiên 100% chu kỳ xung nhịp cho cửa sổ ứng dụng và game đang sử dụng.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=specs_win32
            ),
            TweakDescriptor(
                tweak_id="cpu_core_unparking",
                category=TweakCategory.CPU,
                title="Mở Khóa Toàn Bộ Nhân CPU (Core Unparking 100%)",
                description="Ngăn Windows đưa các nhân xử lý vào trạng thái ngủ ngắt quãng (Core Parking), giữ mọi core luôn sẵn sàng.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=()
            ),
            TweakDescriptor(
                tweak_id="cpu_mmcss_responsiveness",
                category=TweakCategory.CPU,
                title="Tối Ưu MMCSS System Responsiveness",
                description="Phân bổ đến 90% tài nguyên CPU cho các tác vụ đa phương tiện, phát video và gaming thời gian thực.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=specs_mmcss
            ),
            TweakDescriptor(
                tweak_id="cpu_disable_power_throttling",
                category=TweakCategory.CPU,
                title="Tắt Điều Tiết Xung Nhịp CPU (Disable Power Throttling)",
                description="Ngăn chặn tính năng tiết kiệm điện năng của Windows tự ý bóp nghẹt xung nhịp khi đang chạy nặng.",
                requires_admin=True,
                requires_reboot=False,
                registry_targets=specs_throttling
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
            if tweak_id == "cpu_ultimate_power_plan":
                return self._check_ultimate_power_plan()
            elif tweak_id == "cpu_core_unparking":
                return self._check_core_unparking()
            elif tweak_id in self.descriptors:
                return self._check_registry_tweak(self.descriptors[tweak_id])
            return TweakState.ERROR

    def get_all_status(self) -> Dict[str, TweakState]:
        with self._lock:
            return {tid: self.get_status(tid) for tid in self.descriptors}

    def _get_active_power_scheme_guid(self) -> Optional[str]:
        try:
            res = run_cmd(["powercfg", "/getactivescheme"], timeout=5)
            if res.returncode == 0:
                m = re.search(r"([0-9a-fA-F\-]{36})", res.stdout)
                if m:
                    return m.group(1).lower()
        except Exception:
            pass
        return None

    def _check_ultimate_power_plan(self) -> TweakState:
        active_guid = self._get_active_power_scheme_guid()
        if not active_guid:
            return TweakState.DEFAULT

        if active_guid == ULTIMATE_PERF_BASE_GUID.lower():
            return TweakState.OPTIMIZED

        # Kiểm tra xem scheme hiện tại có tên 'Ultimate' hay không
        try:
            res = run_cmd(["powercfg", "/getactivescheme"], timeout=5)
            if res.returncode == 0 and "ultimate" in res.stdout.lower():
                return TweakState.OPTIMIZED
        except Exception:
            pass
        return TweakState.DEFAULT

    def _check_core_unparking(self) -> TweakState:
        try:
            res = run_cmd(
                ["powercfg", "/q", "SCHEME_CURRENT", SUB_PROCESSOR_GUID, CPMINCORES_SETTING_GUID],
                timeout=5
            )
            if res.returncode == 0:
                # Tìm dòng: Current AC Power Setting Index: 0x00000064 (64 hex = 100 dec)
                m = re.search(r"Current AC Power Setting Index:\s*0x([0-9a-fA-F]+)", res.stdout)
                if m:
                    val = int(m.group(1), 16)
                    if val == 100:
                        return TweakState.OPTIMIZED
        except Exception:
            pass
        return TweakState.DEFAULT

    def _get_current_cpmincores(self) -> Tuple[Optional[int], Optional[int]]:
        """Đọc chỉ số CPMINCORES hiện tại (AC, DC) từ powercfg query."""
        try:
            res = run_cmd(
                ["powercfg", "/q", "SCHEME_CURRENT", SUB_PROCESSOR_GUID, CPMINCORES_SETTING_GUID],
                timeout=5
            )
            if res.returncode == 0:
                m_ac = re.search(r"Current AC Power Setting Index:\s*0x([0-9a-fA-F]+)", res.stdout)
                m_dc = re.search(r"Current DC Power Setting Index:\s*0x([0-9a-fA-F]+)", res.stdout)
                ac_val = int(m_ac.group(1), 16) if m_ac else None
                dc_val = int(m_dc.group(1), 16) if m_dc else None
                return ac_val, dc_val
        except Exception:
            pass
        return None, None

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

            # Sao lưu Registry targets trước khi ghi (nếu không chạy ở chế độ batch)
            snapshot_id = None
            if create_snapshot and desc.registry_targets:
                snapshot = self.backup_service.create_snapshot(
                    category=TweakCategory.CPU,
                    targets=list(desc.registry_targets)
                )
                snapshot_id = snapshot.snapshot_id

            try:
                if tweak_id == "cpu_ultimate_power_plan":
                    return self._apply_ultimate_power_plan(create_snapshot=create_snapshot)
                elif tweak_id == "cpu_core_unparking":
                    return self._apply_core_unparking()
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
                if tweak_id == "cpu_ultimate_power_plan":
                    return self._revert_ultimate_power_plan()
                elif tweak_id == "cpu_core_unparking":
                    return self._revert_core_unparking()
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
    def _apply_ultimate_power_plan(self, create_snapshot: bool = True) -> TweakExecutionResult:
        active_before = self._get_active_power_scheme_guid()

        # Sao lưu scheme hiện tại nếu được yêu cầu
        if create_snapshot:
            self.backup_service.create_snapshot(
                category=TweakCategory.CPU,
                targets=[],
                power_scheme_guid_before=active_before
            )

        # Kiểm tra xem Ultimate Scheme đã tồn tại trong danh sách powercfg chưa
        target_guid = None
        list_res = run_cmd(["powercfg", "/list"], timeout=10)
        if list_res.returncode == 0:
            lines = list_res.stdout.splitlines()
            for line in lines:
                if "ultimate" in line.lower():
                    m = re.search(r"([0-9a-fA-F\-]{36})", line)
                    if m:
                        target_guid = m.group(1)
                        break

        # Nếu chưa có, nhân bản từ GUID gốc của Ultimate Performance
        if not target_guid:
            dup_res = run_cmd(["powercfg", "/duplicatescheme", ULTIMATE_PERF_BASE_GUID], timeout=10)
            if dup_res.returncode == 0:
                m = re.search(r"([0-9a-fA-F\-]{36})", dup_res.stdout)
                if m:
                    target_guid = m.group(1)
            else:
                target_guid = ULTIMATE_PERF_BASE_GUID

        if not target_guid:
            target_guid = ULTIMATE_PERF_BASE_GUID

        # Kích hoạt scheme
        act_res = run_cmd(["powercfg", "/setactive", target_guid], timeout=10)
        if act_res.returncode == 0:
            return TweakExecutionResult(
                tweak_id="cpu_ultimate_power_plan",
                success=True,
                new_state=TweakState.OPTIMIZED,
                message=f"Đã kích hoạt Ultimate Performance Power Plan ({target_guid})."
            )
        return TweakExecutionResult(
            tweak_id="cpu_ultimate_power_plan",
            success=False,
            new_state=TweakState.ERROR,
            message=f"Không thể kích hoạt scheme: {act_res.stderr or act_res.stdout}"
        )

    def _revert_ultimate_power_plan(self) -> TweakExecutionResult:
        # Tìm bản sao lưu gần nhất xem scheme trước là gì
        snaps = self.backup_service.list_snapshots(TweakCategory.CPU)
        guid_to_restore = BALANCED_SCHEME_GUID

        for s in snaps:
            snap_obj = self.backup_service.load_snapshot(s["snapshot_id"])
            if snap_obj and snap_obj.power_scheme_guid_before:
                guid_to_restore = snap_obj.power_scheme_guid_before
                break

        res = run_cmd(["powercfg", "/setactive", guid_to_restore], timeout=10)
        if res.returncode == 0:
            return TweakExecutionResult(
                tweak_id="cpu_ultimate_power_plan",
                success=True,
                new_state=TweakState.DEFAULT,
                message=f"Đã khôi phục Power Scheme ({guid_to_restore})."
            )
        return TweakExecutionResult(
            tweak_id="cpu_ultimate_power_plan",
            success=False,
            new_state=TweakState.ERROR,
            message=f"Lỗi hoàn tác scheme: {res.stderr or res.stdout}"
        )

    def _apply_core_unparking(self) -> TweakExecutionResult:
        # Ghi nhận giá trị CPMINCORES ban đầu của người dùng/OEM trước khi áp dụng
        ac_before, dc_before = self._get_current_cpmincores()
        if ac_before is not None or dc_before is not None:
            self._saved_cpmincores = (
                ac_before if ac_before is not None else 5,
                dc_before if dc_before is not None else 5
            )

        # Đặt CPMINCORES = 100% cho cả cắm sạc (AC) và pin (DC)
        cmd_ac = [
            "powercfg", "-setacvalueindex", "SCHEME_CURRENT",
            SUB_PROCESSOR_GUID, CPMINCORES_SETTING_GUID, "100"
        ]
        cmd_dc = [
            "powercfg", "-setdcvalueindex", "SCHEME_CURRENT",
            SUB_PROCESSOR_GUID, CPMINCORES_SETTING_GUID, "100"
        ]
        cmd_act = ["powercfg", "-setactive", "SCHEME_CURRENT"]

        r_ac = run_cmd(cmd_ac, timeout=10)
        r_dc = run_cmd(cmd_dc, timeout=10)
        r_act = run_cmd(cmd_act, timeout=10)

        if r_ac.returncode == 0 and r_act.returncode == 0:
            return TweakExecutionResult(
                tweak_id="cpu_core_unparking",
                success=True,
                new_state=TweakState.OPTIMIZED,
                message="Đã unpark 100% nhân CPU (CPMINCORES = 100%)."
            )
        return TweakExecutionResult(
            tweak_id="cpu_core_unparking",
            success=False,
            new_state=TweakState.ERROR,
            message=f"Lỗi cấu hình Core Unparking: {r_ac.stderr or r_ac.stdout}"
        )

    def _revert_core_unparking(self) -> TweakExecutionResult:
        # Khôi phục CPMINCORES về giá trị ban đầu đã lưu (mặc định fallback là 5%)
        ac_val = 5
        dc_val = 5
        if self._saved_cpmincores:
            ac_val, dc_val = self._saved_cpmincores

        cmd_ac = [
            "powercfg", "-setacvalueindex", "SCHEME_CURRENT",
            SUB_PROCESSOR_GUID, CPMINCORES_SETTING_GUID, str(ac_val)
        ]
        cmd_dc = [
            "powercfg", "-setdcvalueindex", "SCHEME_CURRENT",
            SUB_PROCESSOR_GUID, CPMINCORES_SETTING_GUID, str(dc_val)
        ]
        cmd_act = ["powercfg", "-setactive", "SCHEME_CURRENT"]

        r_ac = run_cmd(cmd_ac, timeout=10)
        r_dc = run_cmd(cmd_dc, timeout=10)
        r_act = run_cmd(cmd_act, timeout=10)

        if r_ac.returncode == 0 and r_act.returncode == 0:
            return TweakExecutionResult(
                tweak_id="cpu_core_unparking",
                success=True,
                new_state=TweakState.DEFAULT,
                message=f"Đã khôi phục trạng thái Core Parking ban đầu (AC: {ac_val}%, DC: {dc_val}%)."
            )
        return TweakExecutionResult(
            tweak_id="cpu_core_unparking",
            success=False,
            new_state=TweakState.ERROR,
            message=f"Lỗi hoàn tác Core Parking: {r_ac.stderr or r_ac.stdout}"
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

        return TweakExecutionResult(
            tweak_id=desc.tweak_id,
            success=True,
            new_state=TweakState.OPTIMIZED,
            message=f"Đã áp dụng tối ưu: {desc.title}",
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
            message=f"Đã khôi phục mặc định: {desc.title}"
        )

    # -------------------------------------------------------------
    # BATCH OPERATIONS
    # -------------------------------------------------------------
    def quick_apply_all(self) -> Dict[str, TweakExecutionResult]:
        with self._lock:
            # Thu thập toàn bộ targets để chụp snapshot chung 1 lần
            all_targets = []
            for d in self.descriptors.values():
                all_targets.extend(d.registry_targets)

            active_before = self._get_active_power_scheme_guid()
            self.backup_service.create_snapshot(
                category=TweakCategory.CPU,
                targets=all_targets,
                power_scheme_guid_before=active_before,
                snapshot_id=f"cpu_quick_apply_batch"
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
