import csv

# Tranco's top entries include infrastructure domains that aren't real websites
SKIP = ("akamai", "amazonaws", "cloudfront", "googleapis", "gstatic",
        "googleusercontent", "doubleclick", "root-servers", "azure",
        "windows.net", "apple-dns", "fastly", "edgekey", "trafficmanager",
        "gtld-servers", "akadns", "office.net", "microsoftonline")

rows = []
with open("data/tranco.csv") as f:
    for rank, domain in csv.reader(f):
        if any(s in domain for s in SKIP):
            continue
        rows.append(("global", domain))
        if len(rows) == 150:
            break

with open("data/india.csv", newline="") as f:
    for r in csv.DictReader(f):
        rows.append((r["category"], r["domain"]))

with open("data/domains.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["category", "domain"])
    w.writerows(rows)

print(f"Wrote {len(rows)} domains to data/domains.csv")