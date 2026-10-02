#!/usr/bin/env python3
import os
import sys
import socket
import ipaddress
import threading
import queue
import time
import platform

# ========== تلاش برای نصب خودکار colorama در صورت نبود ==========
try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
except ImportError:
    # اگر colorama نصب نیست، کلاس‌های جایگزین ساده تعریف می‌کنیم
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'
    class Style:
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        NORMAL = '\033[22m'
    class Back:
        BLACK = '\033[40m'
        RED = '\033[41m'
        GREEN = '\033[42m'
        YELLOW = '\033[43m'
        BLUE = '\033[44m'
        MAGENTA = '\033[45m'
        CYAN = '\033[46m'
        WHITE = '\033[47m'
        RESET = '\033[0m'

# ========== توابع تنظیم خودکار ==========

def get_optimal_workers():
    cpu_count = os.cpu_count() or 1
    workers = min(cpu_count * 8, 200)
    return max(workers, 20)

def get_optimal_queue_size():
    try:
        import psutil
        mem = psutil.virtual_memory()
        if mem.available > 2 * 1024**3:  # 2 GB
            return 2000
        else:
            return 500
    except ImportError:
        return 1000

def get_optimal_timeout():
    return 1.0

# ========== هدر جذاب ==========

def print_banner(port, total_ips, workers, queue_size, timeout):
    os.system('cls' if os.name == 'nt' else 'clear')  # پاک کردن صفحه
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}╔════════════════════════════════════════════════════════════════╗
║                    🔥  IP SCANNER PRO  🔥                    ║
║                  Advanced Port Scanner v2.0                  ║
╚════════════════════════════════════════════════════════════════╝{Style.NORMAL}

{Fore.YELLOW}[+] Target Port       : {Fore.WHITE}{port}
{Fore.YELLOW}[+] Total IPs to scan : {Fore.WHITE}{total_ips:,}
{Fore.YELLOW}[+] Workers           : {Fore.WHITE}{workers}
{Fore.YELLOW}[+] Queue Size        : {Fore.WHITE}{queue_size}
{Fore.YELLOW}[+] Timeout           : {Fore.WHITE}{timeout}s
{Fore.YELLOW}[+] System            : {Fore.WHITE}{platform.system()} {platform.release()} ({os.cpu_count()} cores)
{Fore.YELLOW}[+] Output File       : {Fore.WHITE}open_ports_{port}.txt

{Fore.MAGENTA}{Style.BRIGHT}➜ Scanning started ...{Style.NORMAL}
"""
    print(banner)

# ========== توابع اصلی ==========

def scan_port(ip, port, timeout):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def worker(q, port, timeout, stats, output_file):
    """کارگر: اسکن، به‌روزرسانی آمار، نوشتن نتیجه"""
    while True:
        try:
            ip = q.get(timeout=1)
        except queue.Empty:
            break

        if ip is None:
            q.task_done()
            break

        # اسکن
        is_open = scan_port(ip, port, timeout)

        # به‌روزرسانی آمار با قفل
        with stats['lock']:
            stats['scanned'] += 1
            if is_open:
                stats['open'] += 1
                # چاپ و نوشتن فوری
                output_file.write(f"{ip}:{port}\n")
                output_file.flush()
                # نمایش با رنگ سبز
                print(f"{Fore.GREEN}[+] {ip}:{port} is OPEN{Fore.RESET}")

            # نمایش پیشرفت هر ۵۰۰ آی‌پی
            if stats['scanned'] % 500 == 0 or stats['scanned'] == stats['total']:
                progress = (stats['scanned'] / stats['total']) * 100 if stats['total'] else 0
                bar_length = 40
                filled = int(bar_length * stats['scanned'] // stats['total']) if stats['total'] else 0
                bar = '█' * filled + '░' * (bar_length - filled)
                sys.stdout.write(f"\r{Fore.CYAN}Progress: [{bar}] {progress:.1f}%  |  "
                                 f"Scanned: {stats['scanned']:,}  |  "
                                 f"{Fore.GREEN}Open: {stats['open']}{Fore.RESET}   ")
                sys.stdout.flush()

        q.task_done()

def main():
    if len(sys.argv) != 3:
        print(f"{Fore.RED}Usage: python scanner.py <ip_file> <port>{Fore.RESET}")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        port = int(sys.argv[2])
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print(f"{Fore.RED}Port must be a number between 1 and 65535{Fore.RESET}")
        sys.exit(1)

    # تنظیمات خودکار
    workers = get_optimal_workers()
    queue_size = get_optimal_queue_size()
    timeout = get_optimal_timeout()

    # ========== خواندن فایل و شمارش کل آی‌پی‌ها (برای پیشرفت) ==========
    total_ips = 0
    cidr_list = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                cidr = line.strip()
                if not cidr:
                    continue
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    # فقط تعداد آی‌پی‌ها را محاسبه می‌کنیم (برای نمایش)
                    total_ips += sum(1 for _ in network.hosts())
                    cidr_list.append(cidr)
                except ValueError:
                    print(f"{Fore.RED}Invalid CIDR: {cidr}{Fore.RESET}", file=sys.stderr)
    except FileNotFoundError:
        print(f"{Fore.RED}File '{file_path}' not found.{Fore.RESET}")
        sys.exit(1)

    if total_ips == 0:
        print(f"{Fore.RED}No valid IPs found.{Fore.RESET}")
        sys.exit(1)

    # نمایش هدر
    print_banner(port, total_ips, workers, queue_size, timeout)

    # ایجاد فایل خروجی
    output_filename = f"open_ports_{port}.txt"
    with open(output_filename, 'w') as output_file:
        # ایجاد صف
        ip_queue = queue.Queue(maxsize=queue_size)

        # ساختار آمار
        stats = {
            'total': total_ips,
            'scanned': 0,
            'open': 0,
            'lock': threading.Lock()
        }

        # راه‌اندازی کارگرها
        workers_list = []
        for _ in range(workers):
            t = threading.Thread(
                target=worker,
                args=(ip_queue, port, timeout, stats, output_file)
            )
            t.daemon = True
            t.start()
            workers_list.append(t)

        # تولید آی‌پی‌ها و قرار دادن در صف (با کنترل حافظه)
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    cidr = line.strip()
                    if not cidr:
                        continue
                    try:
                        network = ipaddress.ip_network(cidr, strict=False)
                        for ip in network.hosts():
                            ip_queue.put(str(ip))
                    except ValueError:
                        pass  # قبلاً خطا چاپ شده
        except FileNotFoundError:
            pass  # قبلاً بررسی شد

        # ارسال نشانه پایان به کارگرها
        for _ in range(workers):
            ip_queue.put(None)

        # منتظر اتمام پردازش
        ip_queue.join()

        # منتظر پایان کارگرها
        for t in workers_list:
            t.join(timeout=1)

    # نتیجه نهایی
    print(f"\n\n{Fore.GREEN}{Style.BRIGHT}✅ Scan Completed!{Style.NORMAL}")
    print(f"{Fore.YELLOW}Total IPs scanned : {Fore.WHITE}{stats['scanned']:,}")
    print(f"{Fore.GREEN}Open ports found  : {Fore.WHITE}{stats['open']}")
    print(f"{Fore.YELLOW}Results saved to  : {Fore.WHITE}{output_filename}{Fore.RESET}")

if __name__ == "__main__":
    main()
