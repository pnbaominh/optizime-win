import os
import sys
import subprocess
from typing import List, Optional, Union

# Cờ ẩn hoàn toàn cửa sổ console trên Windows
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

def get_hidden_startupinfo() -> Optional[subprocess.STARTUPINFO]:
    """Tạo STARTUPINFO với cờ SW_HIDE để đảm bảo không một cửa sổ CMD/PowerShell nào xuất hiện."""
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        return startupinfo
    return None

def run_cmd(
    cmd: Union[List[str], str],
    timeout: Optional[int] = 15,
    shell: bool = False,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Thực thi lệnh hệ thống một cách an toàn và ẩn 100% cửa sổ giao diện dòng lệnh (CMD/PowerShell).
    Ngăn chặn việc xuất hiện các tab CMD hoặc cửa sổ đen nhấp nháy trên màn hình người dùng.
    """
    if os.name == 'nt':
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = CREATE_NO_WINDOW
        if 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = get_hidden_startupinfo()

    # Mặc định bắt output dưới dạng text utf-8 an toàn
    if 'capture_output' not in kwargs and 'stdout' not in kwargs:
        kwargs['capture_output'] = True
    if 'text' not in kwargs:
        kwargs['text'] = True
    if 'encoding' not in kwargs and kwargs.get('text', False):
        kwargs['encoding'] = 'utf-8'
        kwargs['errors'] = 'replace'

    try:
        return subprocess.run(cmd, timeout=timeout, shell=shell, **kwargs)
    except Exception:
        # Dự phòng nếu lỗi encoding utf-8 thì fallback cp437/mbcs
        if 'encoding' in kwargs:
            kwargs['encoding'] = 'cp437'
            return subprocess.run(cmd, timeout=timeout, shell=shell, **kwargs)
        raise
