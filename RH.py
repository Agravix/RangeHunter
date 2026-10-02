#!/usr/bin/env python3
import os
import sys
import socket
import ipaddress
import threading
import queue
import time
import platform

try:
    from colorama import init, Fore, Style
    init(autoreset=False)
except ImportError:
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[39m'

    class Style:
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        NORMAL = '\033[22m'
        RESET_ALL = '\033[0m'

TOOL_NAME = "RangeHunter"
TOOL_VERSION = "2.1"
BOX_WIDTH = 64
CLEAR_LINE = '\r\033[K'


def get_optimal_workers():
    cpu_count = os.cpu_count() or 1
    return max(min(cpu_count * 8, 200), 20)


def get_optimal_queue_size():
    try:
        import psutil
        if psutil.virtual_memory().available > 2 * 1024 ** 3:
            return 2000
        return 500
    except ImportError:
        return 1000


def get_optimal_timeout():
    return 1.0


def count_hosts(network):
    if network.prefixlen >= network.max_prefixlen - 1:
        return network.num_addresses
    return network.num_addresses - 2


def format_duration(seconds):
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def info(label, value):
    print(f"  {Fore.CYAN}{label:<14}{Fore.WHITE}{Style.DIM} : {Style.NORMAL}{value}{Style.RESET_ALL}")


LOGO_GLYPHS = {
    'R': ["██████╗ ",
          "██╔══██╗",
          "██████╔╝",
          "██╔══██╗",
          "██║  ██║",
          "╚═╝  ╚═╝"],
    'A': [" █████╗ ",
          "██╔══██╗",
          "███████║",
          "██╔══██║",
          "██║  ██║",
          "╚═╝  ╚═╝"],
    'N': ["███╗   ██╗",
          "████╗  ██║",
          "██╔██╗ ██║",
          "██║╚██╗██║",
          "██║ ╚████║",
          "╚═╝  ╚═══╝"],
    'G': [" ██████╗ ",
          "██╔════╝ ",
          "██║  ███╗",
          "██║   ██║",
          "╚██████╔╝",
          " ╚═════╝ "],
    'E': ["███████╗",
          "██╔════╝",
          "█████╗  ",
          "██╔══╝  ",
          "███████╗",
          "╚══════╝"],
    'H': ["██╗  ██╗",
          "██║  ██║",
          "███████║",
          "██╔══██║",
          "██║  ██║",
          "╚═╝  ╚═╝"],
    'U': ["██╗   ██╗",
          "██║   ██║",
          "██║   ██║",
          "██║   ██║",
          "╚██████╔╝",
          " ╚═════╝ "],
    'T': ["████████╗",
          "╚══██╔══╝",
          "   ██║   ",
          "   ██║   ",
          "   ██║   ",
          "   ╚═╝   "],
}


def render_word(word):
    rows = [''] * 6
    for ch in word:
        glyph = LOGO_GLYPHS[ch]
        width = max(len(r) for r in glyph)
        for i in range(6):
            rows[i] += glyph[i].ljust(width)
    return rows


def print_banner(port, total_ips, workers, queue_size, timeout, output_filename):
    os.system('cls' if os.name == 'nt' else 'clear')
    rule = '━' * BOX_WIDTH
    tagline = f"HIGH-SPEED TCP PORT SCANNER   |   v{TOOL_VERSION}   |   HUNT. SCAN. FIND."

    print()
    for row in render_word("RANGE"):
        print(f"{Fore.CYAN}{Style.BRIGHT}{row.center(BOX_WIDTH)}{Style.RESET_ALL}")
    for row in render_word("HUNTER"):
        print(f"{Fore.RED}{Style.BRIGHT}{row.center(BOX_WIDTH)}{Style.RESET_ALL}")
    print()
    print(f"{Fore.WHITE}{Style.DIM}{rule}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.BRIGHT}{tagline.center(BOX_WIDTH)}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.DIM}{rule}{Style.RESET_ALL}")
    print()
    info("Target Port", port)
    info("Total Hosts", f"{total_ips:,}")
    info("Workers", workers)
    info("Queue Size", queue_size)
    info("Timeout", f"{timeout}s")
    info("System", f"{platform.system()} {platform.release()} ({os.cpu_count()} cores)")
    info("Output File", output_filename)
    print()
    print(f"{Fore.WHITE}{Style.DIM}{rule}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}[*] Hunt started{Style.RESET_ALL}")
    print()


def draw_progress(stats):
    scanned = stats['scanned']
    total = stats['total']
    elapsed = time.time() - stats['start']
    rate = scanned / elapsed if elapsed > 0 else 0
    remaining = (total - scanned) / rate if rate > 0 else 0
    percent = (scanned / total) * 100 if total else 0
    bar_length = 30
    filled = int(bar_length * scanned // total) if total else 0
    bar = '#' * filled + '-' * (bar_length - filled)
    sys.stdout.write(
        f"{CLEAR_LINE}{Fore.CYAN}[{bar}] {percent:5.1f}%{Fore.WHITE}  "
        f"{scanned:,}/{total:,}  {rate:,.0f} ip/s  ETA {format_duration(remaining)}  "
        f"{Fore.GREEN}Open: {stats['open']}{Style.RESET_ALL}"
    )
    sys.stdout.flush()


def scan_port(ip, port, timeout):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def worker(q, port, timeout, stats, output_file):
    while True:
        ip = q.get()

        if ip is None:
            q.task_done()
            break

        is_open = scan_port(ip, port, timeout)

        with stats['lock']:
            stats['scanned'] += 1
            if is_open:
                stats['open'] += 1
                output_file.write(f"{ip}:{port}\n")
                output_file.flush()
                sys.stdout.write(f"{CLEAR_LINE}{Fore.GREEN}[+] OPEN   {Fore.WHITE}{ip}:{port}{Style.RESET_ALL}\n")

            if stats['scanned'] % 200 == 0 or stats['scanned'] == stats['total']:
                draw_progress(stats)

        q.task_done()


def main():
    if len(sys.argv) != 3:
        prog = os.path.basename(sys.argv[0])
        print(f"{Fore.RED}[!] Usage: python {prog} <ip_file> <port>{Style.RESET_ALL}")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        port = int(sys.argv[2])
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print(f"{Fore.RED}[!] Port must be a number between 1 and 65535{Style.RESET_ALL}")
        sys.exit(1)

    workers = get_optimal_workers()
    queue_size = get_optimal_queue_size()
    timeout = get_optimal_timeout()

    total_ips = 0
    try:
        with open(file_path, 'r') as f:
            for line in f:
                cidr = line.strip()
                if not cidr:
                    continue
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    total_ips += count_hosts(network)
                except ValueError:
                    print(f"{Fore.YELLOW}[!] Invalid CIDR skipped: {cidr}{Style.RESET_ALL}", file=sys.stderr)
    except FileNotFoundError:
        print(f"{Fore.RED}[!] File '{file_path}' not found{Style.RESET_ALL}")
        sys.exit(1)

    if total_ips == 0:
        print(f"{Fore.RED}[!] No valid IPs found{Style.RESET_ALL}")
        sys.exit(1)

    output_filename = f"open_ports_{port}.txt"
    print_banner(port, total_ips, workers, queue_size, timeout, output_filename)

    ip_queue = queue.Queue(maxsize=queue_size)
    stats = {
        'total': total_ips,
        'scanned': 0,
        'open': 0,
        'lock': threading.Lock(),
        'start': time.time()
    }

    interrupted = False

    with open(output_filename, 'w') as output_file:
        threads = []
        for _ in range(workers):
            t = threading.Thread(
                target=worker,
                args=(ip_queue, port, timeout, stats, output_file),
                daemon=True
            )
            t.start()
            threads.append(t)

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    cidr = line.strip()
                    if not cidr:
                        continue
                    try:
                        network = ipaddress.ip_network(cidr, strict=False)
                    except ValueError:
                        continue
                    for ip in network.hosts():
                        ip_queue.put(str(ip))

            for _ in range(workers):
                ip_queue.put(None)

            ip_queue.join()
            for t in threads:
                t.join(timeout=1)
        except KeyboardInterrupt:
            interrupted = True

    elapsed = time.time() - stats['start']
    rate = stats['scanned'] / elapsed if elapsed > 0 else 0
    line = '━' * BOX_WIDTH

    print(CLEAR_LINE, end='')
    print()
    print(f"{Fore.CYAN}{Style.BRIGHT}{line}")
    if interrupted:
        print(f"{Fore.YELLOW}{'HUNT INTERRUPTED'.center(BOX_WIDTH)}")
    else:
        print(f"{Fore.GREEN}{'HUNT COMPLETED'.center(BOX_WIDTH)}")
    print(f"{Fore.CYAN}{line}{Style.RESET_ALL}")
    print()
    info("Scanned", f"{stats['scanned']:,} / {stats['total']:,}")
    info("Open Ports", f"{Fore.GREEN}{stats['open']}")
    info("Duration", format_duration(elapsed))
    info("Avg Speed", f"{rate:,.0f} ip/s")
    info("Results File", output_filename)
    print()

    if interrupted:
        os._exit(130)


if __name__ == "__main__":
    main()
