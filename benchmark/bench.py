"""
Benchmark ML-KEM-768 vs X25519 using `openssl speed` (OpenSSL >= 3.5).
Runs each benchmark RUNS times and reports the median.
Writes dashboard/benchmark.json.

Run inside Docker:
  docker run --rm -v "${PWD}:/app" pqc-scanner python3 benchmark/bench.py
"""
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone

RUNS = 3
SECONDS = 2
OUT = "dashboard/benchmark.json"


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout + p.stderr


def floats(line):
    return [float(x) for x in re.findall(r"\d+\.\d+", line)]


def parse_kem(out):
    for line in out.splitlines():
        if line.strip().startswith("ML-KEM-768") and "s" in line:
            nums = floats(line)
            if len(nums) >= 3:
                keygen, encaps, decaps = nums[-3:]  # ops per second
                return keygen, encaps, decaps
    raise SystemExit("Could not parse ML-KEM output:\n" + out)


def parse_x25519(out):
    for line in out.splitlines():
        if "X25519" in line and "ecdh" in line.lower():
            nums = floats(line)
            if nums:
                return nums[-1]  # ops per second
    raise SystemExit("Could not parse X25519 output:\n" + out)


def cpu_model():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown"


kem_runs = []
x_runs = []
for i in range(RUNS):
    print("Run", i + 1, "of", RUNS)
    kem_out = run(["openssl", "speed", "-seconds", str(SECONDS),
                   "-kem-algorithms", "ML-KEM-768"])
    kem_runs.append(parse_kem(kem_out))
    x_out = run(["openssl", "speed", "-seconds", str(SECONDS), "ecdhx25519"])
    x_runs.append(parse_x25519(x_out))

keygen = statistics.median(r[0] for r in kem_runs)
encaps = statistics.median(r[1] for r in kem_runs)
decaps = statistics.median(r[2] for r in kem_runs)
x_ops = statistics.median(x_runs)


def us(ops):
    return round(1e6 / ops, 1)


# Per-side handshake cost estimates (microseconds).
# ML-KEM client: keygen + decaps; server: encaps.
# X25519 client and server each do 2 scalar multiplications (keygen + derive),
# approximated as 2 / ops-per-second.
result = {
    "meta": {
        "openssl": run(["openssl", "version"]).strip(),
        "cpu": cpu_model(),
        "runs": RUNS,
        "seconds_per_run": SECONDS,
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Docker on WSL2; median of runs; x25519 side costs approximated as 2 scalar mults.",
    },
    "speed": {
        "ml_kem_768": {
            "keygen_ops_s": round(keygen, 1),
            "encaps_ops_s": round(encaps, 1),
            "decaps_ops_s": round(decaps, 1),
            "keygen_us": us(keygen),
            "encaps_us": us(encaps),
            "decaps_us": us(decaps),
        },
        "x25519": {
            "scalar_mult_ops_s": round(x_ops, 1),
            "scalar_mult_us": us(x_ops),
        },
    },
    "handshake_cost_us": {
        "x25519_client": round(2e6 / x_ops, 1),
        "x25519_server": round(2e6 / x_ops, 1),
        "ml_kem_768_client": round(1e6 / keygen + 1e6 / decaps, 1),
        "ml_kem_768_server": round(1e6 / encaps, 1),
        "hybrid_client": round(2e6 / x_ops + 1e6 / keygen + 1e6 / decaps, 1),
        "hybrid_server": round(2e6 / x_ops + 1e6 / encaps, 1),
    },
    "sizes_bytes": {
        "x25519": {"client_share": 32, "server_share": 32},
        "ml_kem_768": {"client_share": 1184, "server_share": 1088},
        "hybrid_x25519mlkem768": {"client_share": 1216, "server_share": 1120},
    },
}

with open(OUT, "w") as f:
    json.dump(result, f, indent=2)

print(json.dumps(result["speed"], indent=2))
print(json.dumps(result["handshake_cost_us"], indent=2))
print("Saved", OUT)