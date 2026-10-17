"""
Module: core/contracts.py
Description: Định nghĩa hợp đồng dữ liệu nghiêm ngặt (Strict Data Contracts), Enums
             và thẩm định schema tại runtime cho hệ thống tối ưu CPU, GPU và RAM.
             Tuân thủ Zero-Disk Constraint: Chỉ xử lý CPU, GPU, RAM.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Callable, Optional, Tuple, Union

RegistryScalar = Union[int, str, bytes]


class TweakCategory(str, Enum):
    CPU = "CPU"
    GPU = "GPU"
    RAM = "RAM"


class TweakState(str, Enum):
    LOADING = "LOADING"
    OPTIMIZED = "OPTIMIZED"
    DEFAULT = "DEFAULT"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class RegistryRoot(str, Enum):
    HKLM = "HKEY_LOCAL_MACHINE"
    HKCU = "HKEY_CURRENT_USER"


class RegistryValueType(IntEnum):
    REG_SZ = 1
    REG_EXPAND_SZ = 2
    REG_BINARY = 3
    REG_DWORD = 4
    REG_QWORD = 11


@dataclass(frozen=True)
class RegistryTargetSpec:
    root: RegistryRoot
    subkey: str
    value_name: str
    value_type: RegistryValueType
    optimized_value: RegistryScalar
    default_value: RegistryScalar

    def validate(self) -> None:
        if not self.subkey or self.subkey.startswith("\\") or "/" in self.subkey:
            raise ValueError(f"Subkey không hợp lệ (phải dùng chuẩn Windows và không bắt đầu bằng '\\'): {self.subkey}")
        if not self.value_name.strip():
            raise ValueError("Tên giá trị Registry (value_name) không được để trống.")
        if self.value_type == RegistryValueType.REG_DWORD:
            if not isinstance(self.optimized_value, int) or not (0 <= self.optimized_value <= 0xFFFFFFFF):
                raise ValueError(f"Giá trị optimized REG_DWORD vượt ngưỡng 32-bit unsigned int: {self.optimized_value}")
            if not isinstance(self.default_value, int) or not (0 <= self.default_value <= 0xFFFFFFFF):
                raise ValueError(f"Giá trị default REG_DWORD vượt ngưỡng 32-bit unsigned int: {self.default_value}")


@dataclass(frozen=True)
class TweakDescriptor:
    tweak_id: str
    category: TweakCategory
    title: str
    description: str
    requires_admin: bool
    requires_reboot: bool
    registry_targets: Tuple[RegistryTargetSpec, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not self.tweak_id or not self.tweak_id.replace("_", "").isalnum():
            raise ValueError(f"Mã định danh tweak_id không hợp lệ: {self.tweak_id}")
        if not self.title.strip() or not self.description.strip():
            raise ValueError(f"Tiêu đề và mô tả của tweak '{self.tweak_id}' không được để trống.")
        for target in self.registry_targets:
            target.validate()


@dataclass(frozen=True)
class RegistryBackupEntry:
    root: RegistryRoot
    subkey: str
    value_name: str
    value_type: int
    previous_value: Optional[RegistryScalar]
    existed_before: bool

    def validate(self) -> None:
        if not self.subkey or "/" in self.subkey:
            raise ValueError(f"Đường dẫn subkey trong bản sao lưu không hợp lệ: {self.subkey}")
        if self.existed_before and self.previous_value is None:
            raise ValueError(f"Bản ghi sao lưu '{self.value_name}' đánh dấu existed_before=True nhưng previous_value=None.")


@dataclass(frozen=True)
class BackupSnapshot:
    snapshot_id: str
    created_at_iso: str
    category: TweakCategory
    entries: Tuple[RegistryBackupEntry, ...]
    power_scheme_guid_before: Optional[str] = None

    def validate(self) -> None:
        if not self.snapshot_id.strip() or not self.created_at_iso.strip():
            raise ValueError("Thông tin định danh snapshot_id và created_at_iso là bắt buộc.")
        for entry in self.entries:
            entry.validate()


@dataclass(frozen=True)
class TweakExecutionResult:
    tweak_id: str
    success: bool
    new_state: TweakState
    message: str
    requires_reboot: bool = False
    snapshot_id: Optional[str] = None
    error_code: Optional[str] = None


@dataclass(frozen=True)
class RamStatusMetrics:
    total_physical_kb: int
    available_physical_kb: int
    usage_percent: float
    calculated_svchost_threshold_kb: int
    standby_purge_active: bool
    last_purge_timestamp_iso: Optional[str] = None

    def validate(self) -> None:
        if self.total_physical_kb <= 0:
            raise ValueError(f"Tổng dung lượng RAM phải lớn hơn 0 KB: {self.total_physical_kb}")
        if not (0.0 <= self.usage_percent <= 100.0):
            raise ValueError(f"Phần trăm sử dụng RAM nằm ngoài phạm vi [0, 100]: {self.usage_percent}")
        if self.calculated_svchost_threshold_kb < self.total_physical_kb:
            raise ValueError("Ngưỡng SvcHostSplitThresholdInKB không được nhỏ hơn tổng dung lượng RAM vật lý.")


@dataclass(frozen=True)
class TweakRowProps:
    tweak_id: str
    title: str
    description: str
    state: TweakState
    is_loading: bool
    is_disabled: bool
    requires_reboot: bool
    on_toggle: Callable[[str, bool], None]
