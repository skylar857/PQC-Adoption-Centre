import csv
import json
import math
from collections import defaultdict

RESULTS = "data/results.csv"
OUT = "dashboard/summary.json"

# Statuses where we got no usable answer about the server
NO_ANSWER = {"unreachable", "timeout"}


def wilson(k, n, z=1.96):
    """95% Wilson confidence interval for a proportion, in percent."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(100 * (c - m) / d, 1), round(100 * (c + m) / d, 1))


def summarize(rows):
    total = len(rows)
    counts = defaultdict(int)
    for r in rows:
        counts[r["status"]] += 1
    reachable = total - sum(counts[s] for s in NO_ANSWER)
    hybrid = counts["pqc_hybrid"]
    tls13 = hybrid + counts["classical_only"] + counts["pqc_offer_rejected"]
    lo, hi = wilson(hybrid, reachable)
    return {
        "total": total,
        "reachable": reachable,
        "tls13_ok": tls13,
        "pqc_hybrid": hybrid,
        "classical_only": counts["classical_only"],
        "pqc_offer_rejected": counts["pqc_offer_rejected"],
        "no_tls13": counts["no_tls13"],
        "unreachable": counts["unreachable"],
        "timeout": counts["timeout"],
        "pct_of_reachable": round(100 * hybrid / reachable, 1) if reachable else 0,
        "ci95": [lo, hi],
        "pct_of_tls13": round(100 * hybrid / tls13, 1) if tls13 else 0,
    }


with open(RESULTS, newline="") as f:
    rows = list(csv.DictReader(f))

by_cat = defaultdict(list)
for r in rows:
    by_cat[r["category"]].append(r)

summary = {
    "overall": summarize(rows),
    "categories": {c: summarize(rs) for c, rs in sorted(by_cat.items())},
    "hosts": [
        {"category": r["category"], "domain": r["domain"],
         "status": r["status"], "group": r["negotiated_group"]}
        for r in rows
    ],
    "scanned_at": rows[0]["scanned_at"] if rows else "",
}

with open(OUT, "w") as f:
    json.dump(summary, f, indent=2)

# Console table
print(f"{'category':<12}{'total':>6}{'reach.':>8}{'hybrid':>8}{'% reach.':>10}   95% CI")
for name, s in [("OVERALL", summary["overall"])] + list(summary["categories"].items()):
    print(f"{name:<12}{s['total']:>6}{s['reachable']:>8}{s['pqc_hybrid']:>8}"
          f"{s['pct_of_reachable']:>9}%   {s['ci95'][0]}-{s['ci95'][1]}%")