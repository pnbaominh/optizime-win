from typing import Tuple
from core.process_utils import run_cmd

DNS_PROVIDERS = {
    "Cloudflare": ("1.1.1.1", "1.0.0.1"),
    "Google": ("8.8.8.8", "8.8.4.4"),
    "Quad9": ("9.9.9.9", "149.112.112.112"),
}

def flush_dns_cache() -> Tuple[bool, str]:
    """Xóa sạch bộ nhớ đệm DNS bằng lệnh ipconfig /flushdns hoàn toàn ẩn."""
    try:
        res = run_cmd(["ipconfig", "/flushdns"], timeout=10)
        if res.returncode == 0:
            return True, "Đã xóa sạch bộ nhớ đệm DNS (DNS Cache Flushed)."
        return False, res.stderr.strip() or res.stdout.strip()
    except Exception as e:
        return False, str(e)

def set_primary_dns(provider_name: str) -> Tuple[bool, str]:
    """Thiết lập DNS nhanh cho card mạng đang hoạt động."""
    if provider_name not in DNS_PROVIDERS:
        return False, f"Nhà cung cấp DNS '{provider_name}' không hợp lệ."

    pri_dns, sec_dns = DNS_PROVIDERS[provider_name]
    ps_cmd = (
        f"$adapter = Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }} | Select-Object -First 1; "
        f"if ($adapter) {{ "
        f"  Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses ('{pri_dns}', '{sec_dns}'); "
        f"  Write-Output 'OK' "
        f"}} else {{ Write-Error 'No active adapter' }}"
    )
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
    try:
        res = run_cmd(cmd, timeout=15)
        if res.returncode == 0 and "OK" in res.stdout:
            flush_dns_cache()
            return True, f"Đã áp dụng {provider_name} DNS ({pri_dns}, {sec_dns}) thành công."
        return False, res.stderr.strip() or "Không tìm thấy card mạng đang kết nối Internet."
    except Exception as e:
        return False, str(e)

def reset_dns_to_dhcp() -> Tuple[bool, str]:
    """Khôi phục thiết lập DNS về tự động (DHCP)."""
    ps_cmd = (
        "$adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1; "
        "if ($adapter) { "
        "  Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ResetServerAddresses; "
        "  Write-Output 'OK' "
        "} else { Write-Error 'No active adapter' }"
    )
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
    try:
        res = run_cmd(cmd, timeout=15)
        if res.returncode == 0 and "OK" in res.stdout:
            flush_dns_cache()
            return True, "Đã khôi phục DNS về mặc định tự động (DHCP)."
        return False, res.stderr.strip() or "Lỗi khi khôi phục DNS."
    except Exception as e:
        return False, str(e)
