#!/usr/bin/env python3
"""
Recheck hosts that did not give a clean answer in the main scan.
Run inside Docker (OpenSSL 3.5):
  docker run --rm -v "${PWD}:/app" pqc-scanner python3 scanner/recheck.py
"""
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor

HOSTS = [
    "www.maharashtra.gov.in",
    "www.gujarat.gov.in",
    "www.rajasthan.gov.in",
    "www.wb.gov.in",
    "www.bihar.gov.in",
    "www.imd.gov.in",
    "www.nitdgp.ac.in",
    "www.mu.ac.in",
    "www.unionbankofindia.co.in",
    "www.bankofmaharashtra.in",
    "www.karurvysyabank.co.in",
    "www.citibank.co.in",
]


def sh(args):
    try:
        p = subprocess.run(args, input="", capture_output=True, text=True, timeout=15)
        return p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"


def proto(out):
    if out == "TIMEOUT":
        return "timeout"
    m = re.search(r"Protocol\s*:\s*(\S+)", out)
    return m.group(1) if m else "fail"


def check(host):
    try:
        socket.gethostbyname(host)
    except OSError:
        return "%-30s DNS FAIL (hostname does not resolve)" % host
    base = ["openssl", "s_client", "-connect", host + ":443", "-servername", host]
    a = proto(sh(base + ["-tls1_3", "-groups", "X25519MLKEM768:X25519"]))
    b = proto(sh(base + ["-tls1_3", "-groups", "X25519"]))
    c = proto(sh(base + ["-tls1_2"]))
    return "%-30s dns=ok  hybrid_offer=%-8s x25519_only=%-8s tls12=%s" % (host, a, b, c)


with ThreadPoolExecutor(max_workers=6) as ex:
    for line in ex.map(check, HOSTS):
        print(line)
