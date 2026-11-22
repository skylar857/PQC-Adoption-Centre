#!/usr/bin/env python3
"""
Provider (CDN / edge) attribution for scanned hosts.

For every reachable host in data/results.csv, sends ONE plain `GET /` over HTTPS
(no redirects followed, body not read) and classifies the serving provider from
response headers. Then breaks down hybrid-PQC hosts by provider per category.

Header-based attribution is a lower bound: some sites strip identifying headers.

Run with your normal Python from the project folder:
  python analysis/providers.py

Writes: data/providers.csv, dashboard/providers.json
"""
import csv
import http.client
import json
import ssl
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

RESULTS = "data/results.csv"
OUT_CSV = "data/providers.csv"
OUT_JSON = "dashboard/providers.json"
UA = "Mozilla/5.0 (compatible; pqc-adoption-research/1.0; single passive request)"
REACHABLE = ("pqc_hybrid", "classical_only", "pqc_offer_rejected", "no_tls13")
UNKNOWN = ("other/unidentified", "no_http_response")
ctx = ssl.create_default_context()


def fetch(host):
    try:
        c = http.client.HTTPSConnection(host, timeout=10, context=ctx)
        c.request("GET", "/", headers={"User-Agent": UA, "Accept": "*/*"})
        r = c.getresponse()
        h = {k.lower(): v for k, v in r.getheaders()}
        c.close()
        return h
    except Exception:
        return None


def classify(h):
    if h is None:
        return "no_http_response"
    srv = h.get("server", "").lower()
    via = h.get("via", "").lower()
    keys = " ".join(h)
    if "cf-ray" in h or "cloudflare" in srv:
        return "Cloudflare"
    if "x-amz-cf-id" in h or "cloudfront" in via or "cloudfront" in srv:
        return "CloudFront"
    if "akamai" in srv or "x-akamai" in keys or "akamai-" in keys:
        return "Akamai"
    if "x-fastly-request-id" in h or "fastly" in via or h.get("x-served-by", "").startswith("cache-"):
        return "Fastly"
    if "x-azure-ref" in h or "x-msedge-ref" in h:
        return "Azure Front Door"
    if srv in ("gws", "gse", "esf", "sffe") or "google" in srv or "x-goog" in keys:
        return "Google"
    if "proxygen" in srv or "x-fb-" in keys:
        return "Meta"
    if srv == "apple":
        return "Apple"
    if "awselb" in srv or "amazons3" in srv:
        return "AWS"
    if "x-iinfo" in h or "incapsula" in keys or "imperva" in srv:
        return "Imperva"
    if "x-sucuri-id" in h or "sucuri" in srv:
        return "Sucuri"
    return "other/unidentified"


def probe(row):
    h = fetch(row["domain"])
    return {
        "domain": row["domain"],
        "category": row["category"],
        "status": row["status"],
        "provider": classify(h),
        "server_header": (h or {}).get("server", ""),
    }


def agg(rs):
    hy = Counter(r["provider"] for r in rs if r["status"] == "pqc_hybrid")
    al = Counter(r["provider"] for r in rs)
    h = sum(hy.values())
    known = sum(v for k, v in hy.items() if k not in UNKNOWN)
    return {
        "reachable": len(rs),
        "hybrid": h,
        "hybrid_by_provider": dict(hy),
        "all_by_provider": dict(al),
        "hybrid_via_known_provider_pct": round(100 * known / h, 1) if h else 0,
    }


with open(RESULTS, newline="") as f:
    rows = [r for r in csv.DictReader(f) if r["status"] in REACHABLE]

with ThreadPoolExecutor(max_workers=20) as ex:
    out = list(ex.map(probe, rows))

with open(OUT_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=out[0].keys())
    w.writeheader()
    w.writerows(out)

by_cat = defaultdict(list)
for r in out:
    by_cat[r["category"]].append(r)

summary = {
    "overall": agg(out),
    "categories": {c: agg(rs) for c, rs in sorted(by_cat.items())},
    "hosts": out,
}
with open(OUT_JSON, "w") as f:
    json.dump(summary, f, indent=2)

# Console report
for name, rs in [("OVERALL", out)] + sorted(by_cat.items()):
    a = agg(rs)
    print("\n%s: %d reachable, %d hybrid, %s%% of hybrid hosts via an identified provider"
          % (name, a["reachable"], a["hybrid"], a["hybrid_via_known_provider_pct"]))
    for p, c in Counter(a["hybrid_by_provider"]).most_common():
        print("   hybrid via %-22s %d" % (p, c))

print("\nHybrid rate by provider (all categories):")
tot = Counter(r["provider"] for r in out)
hyb = Counter(r["provider"] for r in out if r["status"] == "pqc_hybrid")
for p, n in tot.most_common():
    print("   %-22s %3d hosts, %3d hybrid (%d%%)" % (p, n, hyb[p], round(100 * hyb[p] / n)))
print("\nSaved", OUT_CSV, "and", OUT_JSON)
