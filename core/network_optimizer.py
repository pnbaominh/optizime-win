import os
import sys
import socket
import struct
import time
import winreg
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Dict, Any, List, Optional, Callable

from core.process_utils import run_cmd

# =====================================================================
# KHO MÁY CHỦ DNS TOÀN CẦU (DNS PRESETS)
# =====================================================================
DNS_PROVIDERS = {
    "Cloudflare": {
        "primary": "1.1.1.1",
        "secondary": "1.0.0.1",
        "desc": "Tốc độ nhanh nhất thế giới, bảo mật cao, không lưu log.",
        "badge": "Siêu Tốc & Riêng Tư",
        "color": "#38bdf8"
    },
    "Google": {
        "primary": "8.8.8.8",
        "secondary": "8.8.4.4",
        "desc": "Độ ổn định cao nhất toàn cầu, máy chủ phủ khắp thế giới.",
        "badge": "Ổn Định Tuyệt Đối",
        "color": "#34d399"
    },
    "Quad9": {
        "primary": "9.9.9.9",
        "secondary": "149.112.112.112",
        "desc": "Tự động chặn tên miền độc hại, lừa đảo và phần mềm gián điệp.",
        "badge": "Bảo Mật Chặn Mã Độc",
        "color": "#a855f7"
    },
    "AdGuard": {
        "primary": "94.140.14.14",
        "secondary": "94.140.15.15",
        "desc": "Chặn quảng cáo web, trình theo dõi và banner độc hại.",
        "badge": "Chặn Quảng Cáo",
        "color": "#10b981"
    },
    "OpenDNS": {
        "primary": "208.67.222.222",
        "secondary": "208.67.220.220",
        "desc": "Hạ tầng Cisco Enterprise, chống phishing và lọc web mạnh mẽ.",
        "badge": "Cisco Doanh Nghiệp",
        "color": "#f59e0b"
    },
    "NextDNS": {
        "primary": "45.90.28.0",
        "secondary": "45.90.30.0",
        "desc": "Thế hệ DNS hiện đại, độ trễ cực thấp và khả năng tùy biến cao.",
        "badge": "Độ Trễ Thấp",
        "color": "#06b6d4"
    },
    "Mullvad": {
        "primary": "194.242.2.4",
        "secondary": "194.242.2.5",
        "desc": "DNS từ Thụy Điển, tiêu chuẩn quyền riêng tư tối đa và chặn ads.",
        "badge": "Bảo Mật Châu Âu",
        "color": "#fbbf24"
    },
    "Control D": {
        "primary": "76.76.2.0",
        "secondary": "76.76.10.0",
        "desc": "Tối ưu hóa định tuyến quốc tế, chặn malware hiệu quả.",
        "badge": "Định Tuyến Thông Minh",
        "color": "#ec4899"
    },
    "DNS.SB": {
        "primary": "185.222.222.222",
        "secondary": "45.11.45.11",
        "desc": "Tối ưu hóa định tuyến khu vực Châu Á - Thái Bình Dương.",
        "badge": "Tối Ưu Châu Á",
        "color": "#6366f1"
    },
    "CleanBrowsing": {
        "primary": "185.228.168.9",
        "secondary": "185.228.169.9",
        "desc": "Bộ lọc an toàn cho gia đình, chặn web người lớn và mã độc.",
        "badge": "Gia Đình An Toàn",
        "color": "#14b8a6"
    }
}

# =====================================================================
# 1. ĐỘNG CƠ BENCHMARK ĐO ĐỘ TRỄ DNS BẰNG RAW UDP SOCKET (PORT 53)
# =====================================================================
def probe_dns_socket(ip: str, port: int = 53, timeout: float = 1.5) -> float:
    """
    Gửi gói tin DNS Query nhị phân RFC 1035 (A record của connectivitycheck.gstatic.com)
    qua UDP socket trực tiếp tới cổng 53 để đo thời gian phản hồi (RTT) chính xác.
    Trả về thời gian tính bằng mili-giây (ms), hoặc -1.0 nếu timeout/lỗi.
    """
    query_id = 0x5a31
    flags = 0x0100  # Standard query with recursion desired
    header = struct.pack("!HHHHHH", query_id, flags, 1, 0, 0, 0)

    # QNAME: connectivitycheck.gstatic.com
    # \x11connectivitycheck\x07gstatic\x03com\x00
    qname = b"\x11connectivitycheck\x07gstatic\x03com\x00"
    qtype_class = struct.pack("!HH", 1, 1)  # Type A (1), Class IN (1)
    packet = header + qname + qtype_class

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    t0 = time.perf_counter()
    try:
        sock.sendto(packet, (ip, port))
        data, _ = sock.recvfrom(512)
        t1 = time.perf_counter()
        if len(data) >= 12:
            return round((t1 - t0) * 1000.0, 1)
        return -1.0
    except (socket.timeout, OSError):
        return -1.0
    finally:
        try:
            sock.close()
        except Exception:
            pass

def benchmark_single_provider(name: str, info: dict, samples: int = 3) -> Dict[str, Any]:
    """
    Thực hiện đo đạc RTT nhiều lần trên cả Primary và Secondary IP để tính
    avg_latency, min_latency, jitter và packet loss.
    """
    ip = info["primary"]
    results = []
    lost = 0

    for _ in range(samples):
        rtt = probe_dns_socket(ip, timeout=1.2)
        if rtt > 0:
            results.append(rtt)
        else:
            lost += 1
        time.sleep(0.04)

    if not results:
        # Nếu Primary IP rớt mạng, thử Secondary IP
        sec_ip = info.get("secondary", "")
        if sec_ip:
            for _ in range(samples):
                rtt = probe_dns_socket(sec_ip, timeout=1.2)
                if rtt > 0:
                    results.append(rtt)
                else:
                    lost += 1
                time.sleep(0.04)

    if results:
        avg_ms = round(sum(results) / len(results), 1)
        min_ms = round(min(results), 1)
        max_ms = round(max(results), 1)
        jitter = round(max_ms - min_ms, 1)
        loss_pct = round((lost / (len(results) + lost)) * 100, 0)
    else:
        avg_ms = 9999.0
        min_ms = 9999.0
        max_ms = 9999.0
        jitter = 0.0
        loss_pct = 100.0

    return {
        "name": name,
        "primary": info["primary"],
        "secondary": info["secondary"],
        "desc": info["desc"],
        "badge": info["badge"],
        "color": info["color"],
        "avg_ms": avg_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "jitter_ms": jitter,
        "loss_pct": int(loss_pct),
        "is_online": avg_ms < 5000.0
    }

def benchmark_all_dns_parallel(progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
    """
    Chạy benchmark song song tất cả các máy chủ DNS bằng ThreadPoolExecutor.
    Trả về danh sách đã sắp xếp từ máy chủ có tốc độ nhanh nhất đến chậm nhất.
    """
    providers = list(DNS_PROVIDERS.items())
    total = len(providers)
    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(benchmark_single_provider, name, info): name for name, info in providers}
        for fut in as_completed(futures):
            try:
                res = fut.result()
                results.append(res)
            except Exception:
                pass
            completed += 1
            if progress_callback:
                progress_callback(completed, total, futures[fut])

    # Sắp xếp: online trước, sau đó theo avg_ms tăng dần
    results.sort(key=lambda x: (0 if x["is_online"] else 1, x["avg_ms"]))
    return results

# =====================================================================
# 2. CHẨN ĐOÁN MẠNG THỜI GIAN THỰC & CARD MẠNG ĐANG HOẠT ĐỘNG
# =====================================================================
def get_active_adapter_info() -> Dict[str, Any]:
    """
    Đọc thông số chi tiết của card mạng chính đang kết nối Internet
    (Adapter name, IPv4, Default Gateway, DNS hiện tại, Trạng thái).
    """
    info = {
        "name": "Không xác định",
        "description": "",
        "ipv4": "Chưa có kết nối",
        "gateway": "Chưa có gateway",
        "dns": "DHCP (Tự động)",
        "status": "Disconnected",
        "is_wifi": False
    }

    ps_code = r"""
    $rt = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1
    if ($rt) {
        $cfg = Get-NetIPConfiguration -InterfaceIndex $rt.InterfaceIndex -ErrorAction SilentlyContinue
        $ad = Get-NetAdapter -InterfaceIndex $rt.InterfaceIndex -ErrorAction SilentlyContinue
        if ($cfg) {
            [PSCustomObject]@{
                Name = $cfg.InterfaceAlias
                Desc = $cfg.InterfaceDescription
                IPv4 = ($cfg.IPv4Address.IPAddress -join ', ')
                Gateway = ($cfg.IPv4DefaultGateway.NextHop -join ', ')
                DNS = ($cfg.DNSServer.ServerAddresses -join ', ')
                Status = if ($ad) { $ad.Status } else { 'Up' }
                IsWifi = if ($ad -and ($ad.InterfaceDescription -match 'Wi-Fi|Wireless|802\.11')) { $true } else { $false }
            } | ConvertTo-Json -Compress
        }
    }
    """
    try:
        res = run_cmd(["powershell", "-NoProfile", "-Command", ps_code], timeout=6)
        if res.returncode == 0 and res.stdout.strip():
            import json
            data = json.loads(res.stdout.strip())
            info["name"] = data.get("Name") or "Local Adapter"
            info["description"] = data.get("Desc") or ""
            info["ipv4"] = data.get("IPv4") or "N/A"
            info["gateway"] = data.get("Gateway") or "N/A"
            info["dns"] = data.get("DNS") or "DHCP (Tự động)"
            info["status"] = data.get("Status") or "Up"
            info["is_wifi"] = bool(data.get("IsWifi", False))
    except Exception:
        pass

    return info

def measure_ping_rtt(target_ip: str, timeout_sec: int = 1) -> float:
    """Đo ping nhanh tới một địa chỉ IP (Gateway hoặc 1.1.1.1). Trả về ms."""
    try:
        res = run_cmd(["ping", "-n", "1", "-w", str(int(timeout_sec * 1000)), target_ip], timeout=timeout_sec + 2)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "time=" in line.lower():
                    part = line.lower().split("time=")[1].split("ms")[0].strip().replace("<", "")
                    return float(part)
                elif "thời gian=" in line.lower():
                    part = line.lower().split("thời gian=")[1].split("ms")[0].strip().replace("<", "")
                    return float(part)
        return -1.0
    except Exception:
        return -1.0

# =====================================================================
# 3. QUẢN LÝ DNS & CHỐNG RÒ RỈ (DNS LEAK PROTECTION)
# =====================================================================
def flush_dns_cache() -> Tuple[bool, str]:
    """Xóa sạch bộ nhớ đệm phân giải tên miền Windows DNS Resolver Cache."""
    try:
        res = run_cmd(["ipconfig", "/flushdns"], timeout=8)
        if res.returncode == 0:
            return True, "Đã làm sạch bộ nhớ đệm phân giải DNS (DNS Cache Flushed)."
        return False, res.stderr.strip() or res.stdout.strip()
    except Exception as e:
        return False, str(e)

def set_primary_dns(provider_name: str) -> Tuple[bool, str]:
    """Thiết lập một nhà cung cấp DNS từ danh mục có sẵn cho card mạng chính."""
    if provider_name not in DNS_PROVIDERS:
        return False, f"Nhà cung cấp DNS '{provider_name}' không tồn tại trong danh mục."

    p_info = DNS_PROVIDERS[provider_name]
    return set_custom_dns(p_info["primary"], p_info.get("secondary", ""), provider_name)

def set_custom_dns(primary_dns: str, secondary_dns: str = "", label: str = "Tùy Chỉnh") -> Tuple[bool, str]:
    """Cài đặt địa chỉ DNS bất kỳ (Primary và Secondary) cho card mạng Internet chính."""
    primary_dns = primary_dns.strip()
    secondary_dns = secondary_dns.strip()

    if not primary_dns:
        return False, "Địa chỉ Primary DNS không được để trống."

    dns_list_str = f"'{primary_dns}'"
    if secondary_dns:
        dns_list_str += f", '{secondary_dns}'"

    ps_code = f"""
    $rt = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1;
    if ($rt) {{
        Set-DnsClientServerAddress -InterfaceIndex $rt.InterfaceIndex -ServerAddresses @({dns_list_str}) -ErrorAction Stop;
        Write-Output 'OK';
    }} else {{
        $ad = Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }} | Select-Object -First 1;
        if ($ad) {{
            Set-DnsClientServerAddress -InterfaceIndex $ad.InterfaceIndex -ServerAddresses @({dns_list_str}) -ErrorAction Stop;
            Write-Output 'OK';
        }} else {{
            Write-Error 'NoActiveAdapter';
        }}
    }}
    """
    try:
        res = run_cmd(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_code], timeout=12)
        if res.returncode == 0 and "OK" in res.stdout:
            flush_dns_cache()
            sec_text = f", {secondary_dns}" if secondary_dns else ""
            return True, f"Đã áp dụng DNS {label} ({primary_dns}{sec_text}) thành công!"
        return False, f"Không thể thiết lập DNS: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, f"Lỗi ngoại lệ khi đổi DNS: {e}"

def reset_dns_to_dhcp() -> Tuple[bool, str]:
    """Khôi phục thiết lập DNS về chế độ tự động nhận từ Router (DHCP)."""
    ps_code = """
    $rt = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1;
    $idx = if ($rt) { $rt.InterfaceIndex } else { (Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1).InterfaceIndex };
    if ($idx) {
        Set-DnsClientServerAddress -InterfaceIndex $idx -ResetServerAddresses -ErrorAction Stop;
        Write-Output 'OK';
    } else {
        Write-Error 'NoActiveAdapter';
    }
    """
    try:
        res = run_cmd(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_code], timeout=12)
        if res.returncode == 0 and "OK" in res.stdout:
            flush_dns_cache()
            return True, "Đã khôi phục thiết lập DNS về mặc định tự động (DHCP)."
        return False, res.stderr.strip() or "Không tìm thấy card mạng phù hợp để reset DNS."
    except Exception as e:
        return False, str(e)

def set_dns_leak_protection(enable: bool) -> Tuple[bool, str]:
    """
    Vô hiệu hóa tính năng Smart Multi-Homed Name Resolution trong Registry
    để ngăn chặn Windows tự động gửi truy vấn DNS đồng thời đến nhiều card mạng (chống rò rỉ DNS Leak).
    """
    val = 1 if enable else 0
    try:
        reg_path = r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.SetValueEx(k, "DisableSmartNameResolution", 0, winreg.REG_DWORD, val)
        if enable:
            return True, "Đã kích hoạt Chống Rò Rỉ DNS (Disable Smart Multi-Homed Resolution)."
        else:
            return True, "Đã khôi phục thiết lập Smart Multi-Homed Resolution về mặc định."
    except Exception as e:
        return False, f"Lỗi cấu hình DNS Leak Protection: {e}"

def set_dns_cache_ttl_optimization(optimize: bool) -> Tuple[bool, str]:
    """
    Tối ưu hóa thời gian lưu cache phân giải tên miền:
    - MaxCacheTtl = 86400 (Giữ cache tên miền thành công lâu hơn để giảm tải truy vấn)
    - MaxNegativeCacheTtl = 5 (Chỉ lưu tên miền bị lỗi trong 5 giây, tránh bị chặn truy cập oan khi mạng vừa sửa)
    """
    try:
        reg_path = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            if optimize:
                winreg.SetValueEx(k, "MaxCacheTtl", 0, winreg.REG_DWORD, 86400)
                winreg.SetValueEx(k, "MaxNegativeCacheTtl", 0, winreg.REG_DWORD, 5)
                return True, "Đã tối ưu hóa thời gian lưu bộ nhớ đệm DNS (TTL = 86400s, Negative TTL = 5s)."
            else:
                try:
                    winreg.DeleteValue(k, "MaxCacheTtl")
                except OSError:
                    pass
                try:
                    winreg.DeleteValue(k, "MaxNegativeCacheTtl")
                except OSError:
                    pass
                return True, "Đã đưa cấu hình bộ nhớ đệm DNS về mặc định của Windows."
    except Exception as e:
        return False, f"Lỗi tối ưu DNS Cache TTL: {e}"

# =====================================================================
# 4. DEEP TCP/IP & SIÊU GIẢM PING GAMING (REGISTRY & NETSH)
# =====================================================================
def set_nagle_algorithm(disable_nagle: bool) -> Tuple[bool, str]:
    """
    Vô hiệu hóa thuật toán Nagle (Nagle's Algorithm Bypass) bằng cách đặt:
    TcpAckFrequency = 1 (Xác nhận gói tin tức thì, loại bỏ Delayed ACK)
    TCPNoDelay = 1 (Không chờ gom cụm gói tin nhỏ)
    TcpDelAckTicks = 0
    trên toàn bộ Network Interfaces trong Registry. Giúp giảm ping rõ rệt trong game online.
    """
    count = 0
    try:
        base_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as base_k:
            subkeys_count, _, _ = winreg.QueryInfoKey(base_k)
            for i in range(subkeys_count):
                guid = winreg.EnumKey(base_k, i)
                try:
                    iface_path = f"{base_path}\\{guid}"
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, iface_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as iface_k:
                        if disable_nagle:
                            winreg.SetValueEx(iface_k, "TcpAckFrequency", 0, winreg.REG_DWORD, 1)
                            winreg.SetValueEx(iface_k, "TCPNoDelay", 0, winreg.REG_DWORD, 1)
                            winreg.SetValueEx(iface_k, "TcpDelAckTicks", 0, winreg.REG_DWORD, 0)
                            count += 1
                        else:
                            for val_name in ("TcpAckFrequency", "TCPNoDelay", "TcpDelAckTicks"):
                                try:
                                    winreg.DeleteValue(iface_k, val_name)
                                except OSError:
                                    pass
                            count += 1
                except Exception:
                    continue

        if disable_nagle:
            return True, f"Đã vô hiệu hóa thuật toán Nagle trên {count} card mạng (Ép truyền gói tin tức thì, giảm ping game)."
        else:
            return True, f"Đã khôi phục thuật toán Nagle về mặc định của Windows trên {count} card mạng."
    except Exception as e:
        return False, f"Lỗi cấu hình thuật toán Nagle: {e}"

def set_network_throttling(disable_throttling: bool) -> Tuple[bool, str]:
    """
    Vô hiệu hóa Network Throttling của Windows:
    - NetworkThrottlingIndex = 0xFFFFFFFF (Tắt cơ chế bóp 10-20% băng thông mạng khi chạy tác vụ media)
    - SystemResponsiveness = 0 (Ưu tiên 100% tài nguyên CPU scheduler cho các ứng dụng mạng và game)
    """
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            if disable_throttling:
                winreg.SetValueEx(k, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xFFFFFFFF)
                winreg.SetValueEx(k, "SystemResponsiveness", 0, winreg.REG_DWORD, 0)
                return True, "Đã vô hiệu hóa Network Throttling & mở khóa tối đa System Responsiveness cho Gaming."
            else:
                winreg.SetValueEx(k, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 10)
                winreg.SetValueEx(k, "SystemResponsiveness", 0, winreg.REG_DWORD, 20)
                return True, "Đã khôi phục Network Throttling về mặc định của Windows."
    except Exception as e:
        return False, f"Lỗi cấu hình Network Throttling: {e}"

def set_qos_bandwidth_limit(remove_limit: bool) -> Tuple[bool, str]:
    """
    Gỡ bỏ giới hạn 20% băng thông dự phòng của Windows QoS Packet Scheduler
    (NonBestEffortLimit = 0).
    """
    try:
        reg_path = r"SOFTWARE\Policies\Microsoft\Windows\Psched"
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            if remove_limit:
                winreg.SetValueEx(k, "NonBestEffortLimit", 0, winreg.REG_DWORD, 0)
                return True, "Đã gỡ bỏ 20% băng thông dự phòng của QoS (Trả lại 100% tốc độ đường truyền)."
            else:
                try:
                    winreg.DeleteValue(k, "NonBestEffortLimit")
                except OSError:
                    pass
                return True, "Đã khôi phục giới hạn băng thông QoS về mặc định."
    except Exception as e:
        return False, f"Lỗi cấu hình QoS: {e}"

def apply_tcp_global_tuning(profile: str = "gaming") -> Tuple[bool, str]:
    """
    Áp dụng cấu hình TCP Global Stack qua netsh int tcp:
    - Profile 'gaming': autotuning=normal, ecn=enabled, rss=enabled, rsc=disabled (loại bỏ độ trễ đệm gói tin), timestamps=disabled
    - Profile 'download': autotuning=normal, ecn=enabled, rss=enabled, rsc=enabled (tối đa hóa tốc độ tải file lớn)
    - Profile 'default': Khôi phục thiết lập gốc của Microsoft
    """
    commands = []
    if profile == "gaming":
        commands = [
            ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
            ["netsh", "int", "tcp", "set", "global", "ecncapability=enabled"],
            ["netsh", "int", "tcp", "set", "global", "rss=enabled"],
            ["netsh", "int", "tcp", "set", "global", "rsc=disabled"],
            ["netsh", "int", "tcp", "set", "global", "timestamps=disabled"],
            ["netsh", "int", "tcp", "set", "global", "nonsackrttresiliency=disabled"]
        ]
        # Thử kích hoạt congestionprovider=ctcp hoặc cubic
        run_cmd(["netsh", "int", "tcp", "set", "supplemental", "template=internet", "congestionprovider=ctcp"], timeout=4)
        run_cmd(["netsh", "int", "tcp", "set", "supplemental", "template=internet", "congestionprovider=cubic"], timeout=4)
    elif profile == "download":
        commands = [
            ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
            ["netsh", "int", "tcp", "set", "global", "ecncapability=enabled"],
            ["netsh", "int", "tcp", "set", "global", "rss=enabled"],
            ["netsh", "int", "tcp", "set", "global", "rsc=enabled"],
            ["netsh", "int", "tcp", "set", "global", "timestamps=disabled"]
        ]
    else:  # default
        commands = [
            ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
            ["netsh", "int", "tcp", "set", "global", "ecncapability=disabled"],
            ["netsh", "int", "tcp", "set", "global", "rss=enabled"],
            ["netsh", "int", "tcp", "set", "global", "rsc=enabled"],
            ["netsh", "int", "tcp", "set", "global", "timestamps=disabled"],
            ["netsh", "int", "tcp", "set", "supplemental", "template=internet", "congestionprovider=default"]
        ]

    for c in commands:
        run_cmd(c, timeout=6)

    desc = "Profile Gaming Siêu Giảm Ping (Tắt RSC, Bật RSS/ECN)" if profile == "gaming" else (
        "Profile Tải Nhanh Băng Thông Lớn (Bật RSC/RSS/ECN)" if profile == "download" else "Thiết Lập Mặc Định Windows"
    )
    return True, f"Đã áp dụng thành công {desc} cho TCP/IP Stack."

# =====================================================================
# 5. TỐI ƯU HÓA PHẦN CỨNG CARD MẠNG (NIC HARDWARE SETTINGS)
# =====================================================================
def set_energy_saving_ethernet(disable: bool) -> Tuple[bool, str]:
    """
    Vô hiệu hóa tính năng tiết kiệm điện năng trên card mạng (Energy Efficient Ethernet & Green Ethernet).
    Ngăn card mạng tự rơi vào chế độ ngủ nông gây drop mạng hoặc lag đột ngột khi chơi game.
    """
    val_str = "0" if disable else "1"
    ps_code = f"""
    $adapters = Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }}
    foreach ($ad in $adapters) {{
        Set-NetAdapterAdvancedProperty -Name $ad.Name -DisplayName '*Energy Efficient Ethernet*' -DisplayValue '{val_str}' -ErrorAction SilentlyContinue
        Set-NetAdapterAdvancedProperty -Name $ad.Name -DisplayName '*Green Ethernet*' -DisplayValue '{val_str}' -ErrorAction SilentlyContinue
        Set-NetAdapterAdvancedProperty -Name $ad.Name -DisplayName '*Gigabit Lite*' -DisplayValue '{val_str}' -ErrorAction SilentlyContinue
    }}
    Write-Output 'OK'
    """
    try:
        res = run_cmd(["powershell", "-NoProfile", "-Command", ps_code], timeout=12)
        if res.returncode == 0:
            msg = "Đã tắt các chế độ tiết kiệm điện (Energy Efficient / Green Ethernet) chống chập chờn rớt mạng." if disable else "Đã bật lại chế độ tiết kiệm điện trên card mạng."
            return True, msg
        return False, res.stderr.strip() or "Không tìm thấy card mạng tương thích."
    except Exception as e:
        return False, str(e)

# =====================================================================
# 6. QUẢN LÝ IPV6 & TRẠNG THÁI TỔNG THỂ
# =====================================================================
def set_ipv6_state(disable: bool) -> Tuple[bool, str]:
    """
    Bật/Tắt IPv6 an toàn qua Registry DisabledComponents.
    Nhiều ISP tại Việt Nam định tuyến IPv6 kém ổn định hơn IPv4, việc tắt IPv6
    giúp giảm giật lag và ngăn chặn rò rỉ DNS qua IPv6 khi dùng VPN.
    """
    val = 0xFF if disable else 0x00
    try:
        reg_path = r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters"
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.SetValueEx(k, "DisabledComponents", 0, winreg.REG_DWORD, val)
        if disable:
            return True, "Đã vô hiệu hóa giao thức IPv6 (Ưu tiên toàn bộ đường truyền qua IPv4 ổn định)."
        else:
            return True, "Đã bật lại giao thức IPv6 mặc định."
    except Exception as e:
        return False, f"Lỗi thiết lập IPv6: {e}"

def get_network_optimization_status() -> Dict[str, Any]:
    """Đọc trạng thái các thiết lập mạng hiện tại để hiển thị trên UI."""
    status = {
        "nagle_disabled": False,
        "throttling_disabled": False,
        "qos_limit_removed": False,
        "dns_leak_protected": False,
        "dns_cache_optimized": False,
        "ipv6_disabled": False,
    }

    # 1. Throttling & Responsiveness
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile") as k:
            nti, _ = winreg.QueryValueEx(k, "NetworkThrottlingIndex")
            status["throttling_disabled"] = (nti & 0xFFFFFFFF) == 0xFFFFFFFF
    except Exception:
        pass

    # 2. QoS NonBestEffortLimit
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Psched") as k:
            limit, _ = winreg.QueryValueEx(k, "NonBestEffortLimit")
            status["qos_limit_removed"] = (limit == 0)
    except Exception:
        pass

    # 3. DNS Leak Protection
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient") as k:
            val, _ = winreg.QueryValueEx(k, "DisableSmartNameResolution")
            status["dns_leak_protected"] = (val == 1)
    except Exception:
        pass

    # 4. DNS Cache TTL
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters") as k:
            ttl, _ = winreg.QueryValueEx(k, "MaxCacheTtl")
            status["dns_cache_optimized"] = (ttl == 86400)
    except Exception:
        pass

    # 5. IPv6 Disabled
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters") as k:
            val, _ = winreg.QueryValueEx(k, "DisabledComponents")
            status["ipv6_disabled"] = (val == 0xFF)
    except Exception:
        pass

    # 6. Nagle (kiểm tra key đầu tiên)
    try:
        base_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as base_k:
            subkeys_count, _, _ = winreg.QueryInfoKey(base_k)
            for i in range(subkeys_count):
                guid = winreg.EnumKey(base_k, i)
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{base_path}\\{guid}") as iface_k:
                        ack, _ = winreg.QueryValueEx(iface_k, "TcpAckFrequency")
                        if ack == 1:
                            status["nagle_disabled"] = True
                            break
                except Exception:
                    continue
    except Exception:
        pass

    return status

# =====================================================================
# 7. BÁC SĨ MẠNG & BỘ SỬA CHỮA MẠNG 1-CLICK (NETWORK DOCTOR)
# =====================================================================
def run_network_doctor(log_callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
    """
    Thực hiện quy trình chẩn đoán và sửa chữa toàn diện kết nối mạng:
    1. Xóa bộ nhớ đệm phân giải DNS (ipconfig /flushdns)
    2. Xóa bảng định tuyến ARP (arp -d * và netsh ip delete arpcache)
    3. Cấp phát lại địa chỉ IP từ Router DHCP (ipconfig /release & /renew)
    4. Khôi phục Winsock Catalog về trạng thái ban đầu (netsh winsock reset)
    5. Thiết lập lại TCP/IP Stack (netsh int ip reset)
    """
    def _log(msg: str):
        if log_callback:
            log_callback(msg)

    _log("--- BẮT ĐẦU QUY TRÌNH BÁC SĨ MẠNG (1-CLICK NETWORK DOCTOR) ---")

    # 1. Flush DNS
    _log("[1/5] Đang xóa sạch bộ nhớ đệm phân giải DNS...")
    ok1, msg1 = flush_dns_cache()
    _log(f"   -> {msg1}")

    # 2. Clear ARP Cache
    _log("[2/5] Đang xóa bộ nhớ đệm bảng phân giải địa chỉ ARP...")
    run_cmd(["arp", "-d", "*"], timeout=5)
    run_cmd(["netsh", "interface", "ip", "delete", "arpcache"], timeout=5)
    _log("   -> Đã làm mới bảng định tuyến ARP.")

    # 3. Renew DHCP Lease
    _log("[3/5] Đang xin cấp phát lại địa chỉ IP mới từ Router DHCP...")
    res_renew = run_cmd(["ipconfig", "/renew"], timeout=15)
    if res_renew.returncode == 0:
        _log("   -> Đã làm mới địa chỉ IP thành công.")
    else:
        _log("   -> Bỏ qua renew DHCP (Có thể đang dùng IP tĩnh).")

    # 4. Reset Winsock Catalog
    _log("[4/5] Đang sửa chữa và khôi phục danh mục Winsock Catalog...")
    res_ws = run_cmd(["netsh", "winsock", "reset"], timeout=8)
    _log(f"   -> {res_ws.stdout.strip() or 'Hoàn tất Winsock Reset'}")

    # 5. Reset TCP/IP Stack
    _log("[5/5] Đang thiết lập lại TCP/IP Stack...")
    res_ip = run_cmd(["netsh", "int", "ip", "reset"], timeout=8)
    _log(f"   -> {res_ip.stdout.strip() or 'Hoàn tất TCP/IP Reset'}")

    _log("--- HOÀN TẤT SỬA CHỮA MẠNG THÀNH CÔNG! ---")
    summary = (
        "Đã hoàn thành sửa chữa mạng toàn diện!\n\n"
        "• Đã xóa sạch bộ nhớ đệm DNS và bảng định tuyến ARP.\n"
        "• Đã cấp phát lại địa chỉ IP từ Router.\n"
        "• Đã sửa chữa danh mục Winsock Catalog và TCP/IP Stack.\n\n"
        "Đường truyền Internet của bạn đã được làm mới hoàn toàn."
    )
    return True, summary

def restart_network_adapter() -> Tuple[bool, str]:
    """
    Khởi động lại card mạng đang hoạt động trong vòng 2-3 giây
    để áp dụng các thiết lập mới mà không cần restart máy tính.
    """
    ps_code = """
    $rt = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1;
    $ad = if ($rt) { Get-NetAdapter -InterfaceIndex $rt.InterfaceIndex } else { Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1 };
    if ($ad) {
        Restart-NetAdapter -Name $ad.Name -ErrorAction Stop;
        Write-Output $ad.Name;
    } else {
        Write-Error 'NoActiveAdapter';
    }
    """
    try:
        res = run_cmd(["powershell", "-NoProfile", "-Command", ps_code], timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            ad_name = res.stdout.strip()
            time.sleep(2)
            flush_dns_cache()
            return True, f"Đã khởi động lại card mạng '{ad_name}' thành công."
        return False, res.stderr.strip() or "Không tìm thấy card mạng chính để khởi động lại."
    except Exception as e:
        return False, f"Lỗi khởi động lại card mạng: {e}"
