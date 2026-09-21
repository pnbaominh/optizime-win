import os
import sys
import ctypes
from ctypes import wintypes
import winreg
from typing import Tuple, Dict, Any, List

from core.process_utils import run_cmd

# Win32 Constants
STANDARD_RIGHTS_REQUIRED = 0x000F0000
SYNCHRONIZE = 0x00100000
PROCESS_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 0xFFFF
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002

# NT SystemInformation Class
SYSTEM_MEMORY_LIST_INFORMATION = 80
MEMORY_PURGE_STANDBY_LIST = 4
MEMORY_EMPTY_WORKING_SETS = 2
MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST = 5

# Toolhelp32
TH32CS_SNAPPROCESS = 0x00000002

# Structures
class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wintypes.DWORD), ('HighPart', wintypes.LONG)]

class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wintypes.DWORD)]

class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wintypes.DWORD), ('Privileges', LUID_AND_ATTRIBUTES * 1)]

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ('dwLength', wintypes.DWORD),
        ('dwMemoryLoad', wintypes.DWORD),
        ('ullTotalPhys', ctypes.c_uint64),
        ('ullAvailPhys', ctypes.c_uint64),
        ('ullTotalPageFile', ctypes.c_uint64),
        ('ullAvailPageFile', ctypes.c_uint64),
        ('ullTotalVirtual', ctypes.c_uint64),
        ('ullAvailVirtual', ctypes.c_uint64),
        ('ullAvailExtendedVirtual', ctypes.c_uint64),
    ]

class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('CommitTotal', ctypes.c_size_t),
        ('CommitLimit', ctypes.c_size_t),
        ('CommitPeak', ctypes.c_size_t),
        ('PhysicalTotal', ctypes.c_size_t),
        ('PhysicalAvailable', ctypes.c_size_t),
        ('SystemCache', ctypes.c_size_t),
        ('KernelTotal', ctypes.c_size_t),
        ('KernelPaged', ctypes.c_size_t),
        ('KernelNonpaged', ctypes.c_size_t),
        ('PageSize', ctypes.c_size_t),
        ('HandleCount', wintypes.DWORD),
        ('ProcessCount', wintypes.DWORD),
        ('ThreadCount', wintypes.DWORD),
    ]

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.POINTER(wintypes.ULONG)),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', ctypes.c_char * 260)
    ]

def enable_privilege(priv_name: str) -> bool:
    """Kích hoạt quyền hệ thống (Privilege) cho tiến trình hiện tại."""
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32

        h_token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_token)):
            return False

        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, priv_name, ctypes.byref(luid)):
            kernel32.CloseHandle(h_token)
            return False

        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

        ret = advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
        err = kernel32.GetLastError()
        kernel32.CloseHandle(h_token)
        return ret != 0 and err == 0
    except Exception:
        return False

def get_detailed_memory_info() -> Dict[str, Any]:
    """
    Đọc thông số chi tiết của hệ thống bộ nhớ RAM thời gian thực
    thông qua GlobalMemoryStatusEx và GetPerformanceInfo.
    """
    info = {
        "total_mb": 0.0,
        "used_mb": 0.0,
        "avail_mb": 0.0,
        "percent_used": 0,
        "cached_mb": 0.0,
        "kernel_total_mb": 0.0,
        "kernel_paged_mb": 0.0,
        "kernel_nonpaged_mb": 0.0,
        "process_count": 0,
    }

    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total_mb = stat.ullTotalPhys / (1024 * 1024)
            avail_mb = stat.ullAvailPhys / (1024 * 1024)
            used_mb = total_mb - avail_mb
            info["total_mb"] = round(total_mb, 1)
            info["avail_mb"] = round(avail_mb, 1)
            info["used_mb"] = round(used_mb, 1)
            info["percent_used"] = int(stat.dwMemoryLoad)
    except Exception:
        pass

    try:
        perf = PERFORMANCE_INFORMATION()
        perf.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
        if ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(perf), ctypes.sizeof(perf)):
            page_bytes = perf.PageSize
            info["cached_mb"] = round((perf.SystemCache * page_bytes) / (1024 * 1024), 1)
            info["kernel_total_mb"] = round((perf.KernelTotal * page_bytes) / (1024 * 1024), 1)
            info["kernel_paged_mb"] = round((perf.KernelPaged * page_bytes) / (1024 * 1024), 1)
            info["kernel_nonpaged_mb"] = round((perf.KernelNonpaged * page_bytes) / (1024 * 1024), 1)
            info["process_count"] = int(perf.ProcessCount)
    except Exception:
        pass

    return info

def get_all_pids() -> List[int]:
    """Lấy danh sách Process ID (PID) đang chạy bằng CreateToolhelp32Snapshot."""
    pids = []
    try:
        h_snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h_snapshot == -1 or h_snapshot == 0:
            return [os.getpid()]

        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)

        if ctypes.windll.kernel32.Process32First(h_snapshot, ctypes.byref(pe)):
            while True:
                if pe.th32ProcessID > 4:  # Bỏ qua System Idle và System
                    pids.append(pe.th32ProcessID)
                if not ctypes.windll.kernel32.Process32Next(h_snapshot, ctypes.byref(pe)):
                    break
        ctypes.windll.kernel32.CloseHandle(h_snapshot)
    except Exception:
        pids = [os.getpid()]
    return pids

def trim_all_working_sets() -> Tuple[bool, str, int, int]:
    """
    Thu gọn Working Set (EmptyWorkingSet & SetProcessWorkingSetSize)
    của tất cả tiến trình đang chạy trong hệ thống.
    Trả về: (thành công, thông báo, số tiến trình đã xử lý, số MB đã giải phóng ước tính)
    """
    enable_privilege("SeDebugPrivilege")
    enable_privilege("SeIncreaseQuotaPrivilege")

    before_info = get_detailed_memory_info()
    pids = get_all_pids()
    trimmed_count = 0

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    for pid in pids:
        try:
            h_proc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
            if h_proc:
                psapi.EmptyWorkingSet(h_proc)
                kernel32.SetProcessWorkingSetSize(h_proc, -1, -1)
                kernel32.CloseHandle(h_proc)
                trimmed_count += 1
        except Exception:
            pass

    # Thu gọn chính tiến trình hiện tại
    try:
        h_self = kernel32.GetCurrentProcess()
        psapi.EmptyWorkingSet(h_self)
        kernel32.SetProcessWorkingSetSize(h_self, -1, -1)
    except Exception:
        pass

    after_info = get_detailed_memory_info()
    freed_mb = max(0, int(after_info["avail_mb"] - before_info["avail_mb"]))

    msg = f"Đã thu gọn Working Set của {trimmed_count} tiến trình."
    if freed_mb > 0:
        msg += f" Thu hồi thêm ~{freed_mb} MB RAM khả dụng."

    return True, msg, trimmed_count, freed_mb

def purge_standby_list() -> Tuple[bool, str, int]:
    """
    Xóa sạch bộ nhớ đệm Standby List qua Windows NT Native API (NtSetSystemInformation).
    Yêu cầu đặc quyền SeProfileSingleProcessPrivilege.
    """
    priv_ok = enable_privilege("SeProfileSingleProcessPrivilege")

    before_info = get_detailed_memory_info()
    ntdll = ctypes.windll.ntdll

    # 1. Purge toàn bộ Standby List (Command 4: MemoryPurgeStandbyList)
    cmd_standby = ctypes.c_int(MEMORY_PURGE_STANDBY_LIST)
    status1 = ntdll.NtSetSystemInformation(
        SYSTEM_MEMORY_LIST_INFORMATION,
        ctypes.byref(cmd_standby),
        ctypes.sizeof(cmd_standby)
    )

    # 2. Thu gọn System Working Sets (Command 2: MemoryEmptyWorkingSets)
    cmd_sys = ctypes.c_int(MEMORY_EMPTY_WORKING_SETS)
    status2 = ntdll.NtSetSystemInformation(
        SYSTEM_MEMORY_LIST_INFORMATION,
        ctypes.byref(cmd_sys),
        ctypes.sizeof(cmd_sys)
    )

    after_info = get_detailed_memory_info()
    freed_mb = max(0, int(after_info["avail_mb"] - before_info["avail_mb"]))

    if status1 == 0:
        msg = "Đã dọn sạch bộ nhớ đệm Standby Cache hệ thống qua NT Native API."
        if freed_mb > 0:
            msg += f" Giải phóng thêm ~{freed_mb} MB RAM."
        return True, msg, freed_mb
    else:
        # Nếu thiếu quyền admin
        if not priv_ok or (status1 & 0xFFFFFFFF) == 0xC0000061:
            return False, "Cần chạy ứng dụng với quyền Administrator để xóa Standby List hệ thống.", 0
        return False, f"NtSetSystemInformation trả về mã lỗi: {hex(status1 & 0xFFFFFFFF)}", 0

def full_memory_purge() -> Tuple[bool, str, int]:
    """
    Thực hiện siêu tối ưu RAM toàn diện:
    1. Thu gọn Working Set của tất cả tiến trình
    2. Dọn sạch Standby List và System Working Sets
    """
    before_info = get_detailed_memory_info()

    trim_ok, trim_msg, count, _ = trim_all_working_sets()
    standby_ok, standby_msg, _ = purge_standby_list()

    after_info = get_detailed_memory_info()
    total_freed_mb = max(0, int(after_info["avail_mb"] - before_info["avail_mb"]))

    msg = f"Đã hoàn tất Siêu Dọn Dẹp RAM ({count} ứng dụng & Standby Cache)."
    if total_freed_mb > 0:
        msg += f" Đã trả lại {total_freed_mb} MB RAM vào vùng nhớ khả dụng!"
    else:
        msg += " Bộ nhớ RAM đã ở trạng thái tối ưu nhất."

    return True, msg, total_freed_mb

# -------------------------------------------------------------
# CẤU HÌNH BỘ NHỚ VĨNH VIỄN KHI KHỞI ĐỘNG LẠI (BOOT PERSISTENT)
# -------------------------------------------------------------

def get_boot_memory_status() -> Dict[str, Any]:
    """Đọc trạng thái các thiết lập bộ nhớ boot vĩnh viễn."""
    status = {
        "sysmain_disabled": False,
        "memory_compression_disabled": False,
        "large_system_cache_app_mode": True,  # LargeSystemCache = 0 là ưu tiên ứng dụng
        "clear_pagefile": False
    }

    # 1. Kiểm tra SysMain Service trong Registry
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\SysMain") as k:
            val, _ = winreg.QueryValueEx(k, "Start")
            status["sysmain_disabled"] = (val == 4)
    except Exception:
        pass

    # 2. Kiểm tra Memory Management Registry
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management") as k:
            try:
                lsc, _ = winreg.QueryValueEx(k, "LargeSystemCache")
                status["large_system_cache_app_mode"] = (lsc == 0)
            except Exception:
                pass

            try:
                cpf, _ = winreg.QueryValueEx(k, "ClearPageFileAtShutdown")
                status["clear_pagefile"] = (cpf == 1)
            except Exception:
                pass
    except Exception:
        pass

    # 3. Kiểm tra MemoryCompression qua PowerShell Get-MMAgent (nhanh)
    try:
        res = run_cmd(["powershell", "-NoProfile", "-Command", "(Get-MMAgent).MemoryCompression"], timeout=5)
        if res.returncode == 0:
            out = res.stdout.strip().lower()
            if "false" in out:
                status["memory_compression_disabled"] = True
            elif "true" in out:
                status["memory_compression_disabled"] = False
    except Exception:
        pass

    return status

def set_sysmain_boot(disable: bool) -> Tuple[bool, str]:
    """Bật/tắt dịch vụ SysMain (Superfetch) lúc khởi động."""
    start_val = 4 if disable else 2
    sc_val = "disabled" if disable else "auto"

    try:
        # Ghi trực tiếp Registry
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\SysMain", 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.SetValueEx(k, "Start", 0, winreg.REG_DWORD, start_val)

        # Chạy sc.exe config
        run_cmd(["sc.exe", "config", "SysMain", f"start= {sc_val}"], timeout=5)

        if disable:
            run_cmd(["net", "stop", "SysMain", "/y"], timeout=5)
            return True, "Đã vô hiệu hóa SysMain (SuperFetch). Windows sẽ không tự nạp ứng dụng vào RAM khi khởi động."
        else:
            run_cmd(["net", "start", "SysMain"], timeout=5)
            return True, "Đã khôi phục dịch vụ SysMain về mặc định."
    except Exception as e:
        return False, f"Lỗi thiết lập SysMain: {e}"

def set_memory_compression_boot(disable: bool) -> Tuple[bool, str]:
    """
    Bật/tắt tính năng Memory Compression trong Windows 10/11.
    Tắt đi sẽ giúp giảm 300MB - 800MB RAM của tiến trình 'System' sau khi restart.
    """
    cmd_name = "Disable-MMAgent" if disable else "Enable-MMAgent"
    ps_cmd = f"{cmd_name} -MemoryCompression -ErrorAction Stop"

    try:
        res = run_cmd(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], timeout=10)
        if res.returncode == 0:
            if disable:
                return True, "Đã tắt Memory Compression. Sau khi khởi động lại, tiến trình System sẽ giảm rõ rệt dung lượng RAM."
            else:
                return True, "Đã bật lại Memory Compression mặc định của Windows."
        return False, f"Lỗi thiết lập Memory Compression: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, f"Ngoại lệ khi chỉnh Memory Compression: {e}"

def set_large_system_cache_boot(prioritize_apps: bool) -> Tuple[bool, str]:
    """
    Cấu hình LargeSystemCache:
    0 = Ưu tiên bộ nhớ vật lý cho các chương trình ứng dụng (App Mode).
    1 = Dành dung lượng bộ nhớ đệm lớn cho hệ thống tập tin (Server/File Cache Mode).
    """
    val = 0 if prioritize_apps else 1
    try:
        reg_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.SetValueEx(k, "LargeSystemCache", 0, winreg.REG_DWORD, val)
        if prioritize_apps:
            return True, "Đã cấu hình LargeSystemCache = 0 (Tối đa hóa RAM vật lý cho ứng dụng)."
        else:
            return True, "Đã cấu hình LargeSystemCache = 1 (Mở rộng bộ nhớ đệm tập tin hệ thống)."
    except Exception as e:
        return False, f"Lỗi cấu hình LargeSystemCache: {e}"

# Tương thích ngược với lời gọi hàm cũ
def trim_memory_working_sets() -> Tuple[bool, str]:
    ok, msg, _, _ = trim_all_working_sets()
    return ok, msg
