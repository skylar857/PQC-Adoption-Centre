#!/usr/bin/env python3
"""
PQC adoption scanner.

Checks which HTTPS hosts negotiate the hybrid post-quantum key exchange
X25519MLKEM768 in a TLS 1.3 handshake. Passive: one normal handshake per host
(plus control handshakes if the hybrid attempt fails).

A handshake counts as successful only if OpenSSL reports a real cipher
("New, TLSv1.x, Cipher is <name>"). OpenSSL prints "Protocol: TLSv1.3" and
"Negotiated TLS1.3 group: <NULL>" even when a handshake FAILS, so those lines
must not be used as proof of success.

Statuses:
  pqc_hybrid          server negotiated X25519MLKEM768
  classical_only      TLS 1.3 works, server picked a non-PQC group
  pqc_offer_rejected  hybrid offer failed, but classical-only TLS 1.3 works
  no_tls13            TLS 1.3 fails, but TLS 1.2 works (server is TLS 1.2 only)
  unreachable         no handshake of any kind succeeded (DNS, timeout, blocked)

Requires OpenSSL >= 3.5 (native ML-KEM). Check with: openssl version

Input  : domains.csv  with header  category,domain
Output : results.csv

Usage  : python3 scanner/scanner_pqc.py data/domains.csv data/results.csv
"""
import csv
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

TIMEOUT = 12
WORKERS = 20

# Success only if a real cipher was agreed: "New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384"
OK_RE = re.compile(r"New,\s*(TLSv[\d.]+),\s*Cipher is\s+(?!\(NONE\))(\S+)")
# Hybrid / KEM groups are printed as "Negotiated TLS1.3 group: <name>"
GROUP_RE = re.compile(r"Negotiated TLS1\.3 group:\s*(\S+)")
# Classical groups are printed as "Peer Temp Key: X25519, 253 bits"
TMPKEY_RE = re.compile(r"Peer Temp Key:\s*(.+?),\s*\d+ bits")
CONNECT_ERR = ("getaddrinfo", "Connection refused", "errno=", "Name or service not known")


def openssl_version() -> str:
    return subprocess.run(["openssl", "version"], capture_output=True, text=True).stdout.strip()


def run_client(host, extra):
    cmd = ["openssl", "s_client", "-connect", f"{host}:443", "-servername", host] + extra
    try:
        p = subprocess.run(cmd, input="", capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    return p.stdout + p.stderr


def handshake(host, groups):
    """TLS 1.3 handshake. Returns (state, group); state is ok / unreachable / failed / timeout."""
    out = run_client(host, ["-tls1_3", "-groups", groups])
    if out is None:
        return "timeout", ""
    if not OK_RE.search(out):
        if any(s in out for s in CONNECT_ERR):
            return "unreachable", ""
        return "failed", ""
    g = GROUP_RE.search(out)
    if g and g.group(1) != "<NULL>":
        return "ok", g.group(1)
    t = TMPKEY_RE.search(out)
    if t:
        return "ok", t.group(1).strip()
    return "ok", "unknown"


def tls12_ok(host):
    """Control check: does the host complete a real TLS 1.2 handshake?"""
    out = run_client(host, ["-tls1_2"])
    if out is None:
        return False
    m = OK_RE.search(out)
    return bool(m and m.group(1) == "TLSv1.2")


def scan(row):
    host = row["domain"].strip()
    # Offer hybrid first, classical as fallback. The group the server picks
    # tells us whether it supports the hybrid.
    st, group = handshake(host, "X25519MLKEM768:X25519")
    proto = ""
    if st == "ok":
        proto = "TLSv1.3"
        status = "pqc_hybrid" if group == "X25519MLKEM768" else "classical_only"
    elif st == "unreachable":
        status = "unreachable"
    else:
        # Hybrid offer failed or timed out. Does a classical-only handshake work?
        st2, group2 = handshake(host, "X25519")
        if st2 == "ok":
            status, group, proto = "pqc_offer_rejected", group2, "TLSv1.3"
        elif st2 == "unreachable":
            status = "unreachable"
        elif tls12_ok(host):
            status, proto = "no_tls13", "TLSv1.2"
        else:
            status = "unreachable"    # nothing worked: do not count as "no TLS 1.3"
    return {
        "category": row["category"],
        "domain": host,
        "status": status,
        "negotiated_group": group,
        "protocol": proto,
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main(inp, outp):
    with open(inp, newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"Scanner: {openssl_version()} | {len(rows)} hosts")
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(scan, rows))
    with open(outp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
    done = sum(r["status"] == "pqc_hybrid" for r in results)
    print(f"Hybrid PQC: {done}/{len(results)}  ->  {outp}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
