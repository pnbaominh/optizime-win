"""
Module: core/registry_backup.py
Description: Dịch vụ sao lưu và phục hồi Registry nguyên tử (RegistryBackupService).
             Sử dụng JSON snapshot, threading.RLock và winreg KEY_WOW64_64KEY.
"""

from __future__ import annotations
import os
import json
import uuid
import winreg
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from core.contracts import (
    TweakCategory,
    RegistryRoot,
    RegistryValueType,
    RegistryTargetSpec,
    RegistryBackupEntry,
    BackupSnapshot,
    RegistryScalar,
)
from core.process_utils import run_cmd


class RegistryBackupService:
    """Quản lý sao lưu và phục hồi trạng thái Registry và Power Scheme an toàn."""

    def __init__(self, backup_dir: Optional[str] = None):
        if backup_dir:
            self.backup_dir = Path(backup_dir).resolve()
        else:
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.backup_dir = (base_dir / "backups" / "hardware_backups").resolve()

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _get_hkey(self, root: RegistryRoot) -> int:
        if root == RegistryRoot.HKLM:
            return winreg.HKEY_LOCAL_MACHINE
        elif root == RegistryRoot.HKCU:
            return winreg.HKEY_CURRENT_USER
        raise ValueError(f"RegistryRoot không được hỗ trợ: {root}")

    def capture_entry(self, root: RegistryRoot, subkey: str, value_name: str) -> RegistryBackupEntry:
        """Đọc và tạo bản chụp của một giá trị Registry cụ thể."""
        hroot = self._get_hkey(root)
        access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        try:
            with winreg.OpenKey(hroot, subkey, 0, access) as key:
                val, val_type = winreg.QueryValueEx(key, value_name)
                # Convert bytes to hex string for json serialization if binary
                if isinstance(val, bytes):
                    val_scalar = val.hex()
                else:
                    val_scalar = val
                entry = RegistryBackupEntry(
                    root=root,
                    subkey=subkey,
                    value_name=value_name,
                    value_type=val_type,
                    previous_value=val_scalar,
                    existed_before=True
                )
        except (FileNotFoundError, OSError, TypeError):
            entry = RegistryBackupEntry(
                root=root,
                subkey=subkey,
                value_name=value_name,
                value_type=int(RegistryValueType.REG_DWORD),
                previous_value=None,
                existed_before=False
            )
        entry.validate()
        return entry

    def create_snapshot(
        self,
        category: TweakCategory,
        targets: List[RegistryTargetSpec],
        power_scheme_guid_before: Optional[str] = None,
        snapshot_id: Optional[str] = None
    ) -> BackupSnapshot:
        """Chụp toàn bộ các Registry targets và lưu thành snapshot JSON."""
        with self._lock:
            sid = snapshot_id or f"{category.value.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            iso_now = datetime.now(timezone.utc).isoformat()

            entries: List[RegistryBackupEntry] = []
            for t in targets:
                entry = self.capture_entry(t.root, t.subkey, t.value_name)
                entries.append(entry)

            snapshot = BackupSnapshot(
                snapshot_id=sid,
                created_at_iso=iso_now,
                category=category,
                entries=tuple(entries),
                power_scheme_guid_before=power_scheme_guid_before
            )
            snapshot.validate()
            self._save_snapshot_to_disk(snapshot)
            return snapshot

    def _save_snapshot_to_disk(self, snapshot: BackupSnapshot) -> Path:
        """Ghi snapshot ra tệp JSON với cơ chế ghi nguyên tử (atomic write)."""
        file_path = self.backup_dir / f"{snapshot.snapshot_id}.json"
        temp_path = self.backup_dir / f"{snapshot.snapshot_id}.tmp"

        data = {
            "snapshot_id": snapshot.snapshot_id,
            "created_at_iso": snapshot.created_at_iso,
            "category": snapshot.category.value,
            "power_scheme_guid_before": snapshot.power_scheme_guid_before,
            "entries": [
                {
                    "root": e.root.value,
                    "subkey": e.subkey,
                    "value_name": e.value_name,
                    "value_type": e.value_type,
                    "previous_value": e.previous_value,
                    "existed_before": e.existed_before
                }
                for e in snapshot.entries
            ]
        }

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if file_path.exists():
            file_path.unlink()
        temp_path.rename(file_path)
        return file_path

    def load_snapshot(self, snapshot_id: str) -> Optional[BackupSnapshot]:
        """Đọc snapshot từ tệp JSON."""
        with self._lock:
            file_path = self.backup_dir / f"{snapshot_id}.json"
            if not file_path.exists():
                return None
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                entries = []
                for item in data.get("entries", []):
                    # Khôi phục bytes nếu là REG_BINARY
                    val = item["previous_value"]
                    if item["value_type"] == int(RegistryValueType.REG_BINARY) and isinstance(val, str):
                        try:
                            val = bytes.fromhex(val)
                        except ValueError:
                            pass
                    entries.append(
                        RegistryBackupEntry(
                            root=RegistryRoot(item["root"]),
                            subkey=item["subkey"],
                            value_name=item["value_name"],
                            value_type=item["value_type"],
                            previous_value=val,
                            existed_before=item["existed_before"]
                        )
                    )

                snapshot = BackupSnapshot(
                    snapshot_id=data["snapshot_id"],
                    created_at_iso=data["created_at_iso"],
                    category=TweakCategory(data["category"]),
                    entries=tuple(entries),
                    power_scheme_guid_before=data.get("power_scheme_guid_before")
                )
                snapshot.validate()
                return snapshot
            except Exception:
                return None

    def restore_snapshot(self, snapshot_id: str) -> Tuple[bool, str]:
        """Khôi phục toàn bộ trạng thái Registry và Power Scheme từ snapshot_id."""
        with self._lock:
            snapshot = self.load_snapshot(snapshot_id)
            if not snapshot:
                return False, f"Không tìm thấy bản sao lưu: {snapshot_id}"

            restored_count = 0
            errors = []

            for entry in snapshot.entries:
                hroot = self._get_hkey(entry.root)
                access = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY

                try:
                    if entry.existed_before:
                        # Ghi lại giá trị cũ
                        with winreg.CreateKeyEx(hroot, entry.subkey, 0, access) as key:
                            winreg.SetValueEx(
                                key,
                                entry.value_name,
                                0,
                                entry.value_type,
                                entry.previous_value
                            )
                        restored_count += 1
                    else:
                        # Khóa trước đó không tồn tại -> Xóa giá trị đã tạo
                        try:
                            with winreg.OpenKey(hroot, entry.subkey, 0, access) as key:
                                winreg.DeleteValue(key, entry.value_name)
                            restored_count += 1
                        except FileNotFoundError:
                            pass
                except Exception as e:
                    errors.append(f"{entry.subkey}\\{entry.value_name}: {e}")

            # Khôi phục power scheme nếu có
            if snapshot.power_scheme_guid_before:
                try:
                    res = run_cmd(["powercfg", "/setactive", snapshot.power_scheme_guid_before], timeout=10)
                    if res.returncode != 0:
                        errors.append(f"Không thể kích hoạt lại power scheme {snapshot.power_scheme_guid_before}")
                except Exception as e:
                    errors.append(f"Lỗi khôi phục power scheme: {e}")

            if errors:
                return False, f"Khôi phục hoàn tất {restored_count} mục nhưng có lỗi: {'; '.join(errors)}"
            return True, f"Đã khôi phục thành công {restored_count} mục từ bản sao lưu {snapshot_id}."

    def list_snapshots(self, category: Optional[TweakCategory] = None) -> List[Dict[str, Any]]:
        """Liệt kê danh sách bản sao lưu có sẵn, sắp xếp theo thời gian mới nhất."""
        with self._lock:
            results = []
            for p in sorted(self.backup_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if category and data.get("category") != category.value:
                        continue
                    results.append({
                        "snapshot_id": data.get("snapshot_id", p.stem),
                        "created_at_iso": data.get("created_at_iso", ""),
                        "category": data.get("category", ""),
                        "entries_count": len(data.get("entries", [])),
                        "file_path": str(p)
                    })
                except Exception:
                    continue
            return results

    def restore_latest_by_category(self, category: TweakCategory) -> Tuple[bool, str]:
        """Khôi phục bản sao lưu gần nhất thuộc một danh mục."""
        snaps = self.list_snapshots(category)
        if not snaps:
            return False, f"Không có bản sao lưu nào cho danh mục {category.value}."
        latest_id = snaps[0]["snapshot_id"]
        return self.restore_snapshot(latest_id)
