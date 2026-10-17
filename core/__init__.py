"""
Core module for Windows Deep Optimizer.
Cung cấp các dịch vụ hệ thống, tối ưu hóa CPU, GPU, RAM, mạng, quyền riêng tư và an toàn.
"""

from core.contracts import (
    TweakCategory,
    TweakState,
    RegistryRoot,
    RegistryValueType,
    RegistryTargetSpec,
    TweakDescriptor,
    RegistryBackupEntry,
    BackupSnapshot,
    TweakExecutionResult,
    RamStatusMetrics,
)
from core.registry_backup import RegistryBackupService
from core.cpu_optimizer import CpuOptimizerService
from core.gpu_optimizer import GpuOptimizerService
from core.ram_optimizer import (
    get_disable_paging_executive,
    set_disable_paging_executive,
    get_svchost_split_status,
    apply_svchost_split_threshold,
    AutoStandbyPurgeWorker,
    get_auto_purge_worker,
)

__all__ = [
    "TweakCategory",
    "TweakState",
    "RegistryRoot",
    "RegistryValueType",
    "RegistryTargetSpec",
    "TweakDescriptor",
    "RegistryBackupEntry",
    "BackupSnapshot",
    "TweakExecutionResult",
    "RamStatusMetrics",
    "RegistryBackupService",
    "CpuOptimizerService",
    "GpuOptimizerService",
    "get_disable_paging_executive",
    "set_disable_paging_executive",
    "get_svchost_split_status",
    "apply_svchost_split_threshold",
    "AutoStandbyPurgeWorker",
    "get_auto_purge_worker",
]
