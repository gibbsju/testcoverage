"""
Generate the suite x worker-type matrix as a markdown table.
"""

import json
from pathlib import Path

BASE = Path(__file__).parent.parent

with open(BASE / "docs" / "coverage_map.json") as f:
    cov_data = json.load(f)

wt_data = cov_data["worker_type_coverage"]

# Classify
def classify_os(wt):
    if "linux" in wt or "kvm" in wt or "netperf" in wt: return "Linux"
    elif "win" in wt: return "Windows"
    elif "osx" in wt: return "macOS"
    elif "bitbar" in wt or "lambda" in wt: return "Android"
    return "Other"

def classify_suite(s):
    if s.startswith("talos-") or s.startswith("browsertime-"): return "perf"
    if s.startswith("awsy"): return "other"
    return "func"

# Order worker-types by OS
os_order = {"Linux": 0, "Windows": 1, "macOS": 2, "Android": 3, "Other": 4}
all_wts = sorted(wt_data.keys(), key=lambda w: (os_order.get(classify_os(w), 4), w))

# Build suite -> wt set
all_suites = set()
suite_wts = {}
for wt, info in wt_data.items():
    for s in info["suites"]:
        all_suites.add(s)
        suite_wts.setdefault(s, set()).add(wt)

all_suites = sorted(all_suites)

# Group suites
groups = {"perf": [], "func": [], "other": []}
for s in all_suites:
    cat = classify_suite(s)
    count = len(suite_wts.get(s, set()))
    groups[cat].append((s, count))

for cat in groups:
    groups[cat].sort(key=lambda x: x[1])

# Shorten worker-type names for column headers
def shorten(wt):
    wt = wt.replace("t-linux-docker-noscratch-amd", "linux-docker")
    wt = wt.replace("t-linux-docker-", "linux-docker-")
    wt = wt.replace("t-linux-", "linux-")
    wt = wt.replace("t-osx-", "osx-")
    wt = wt.replace("t-bitbar-gw-unit-", "bitbar-")
    wt = wt.replace("t-lambda-perf-", "lambda-")
    return wt

short_wts = [shorten(wt) for wt in all_wts]

lines = []
lines.append("# Firefox CI: Suite x Worker-Type Matrix")
lines.append("")
lines.append(f"Generated: 2026-03-31 | {len(all_suites)} suites x {len(all_wts)} worker-types")
lines.append("")
lines.append("Legend: `*` = suite runs on this worker-type | `#` = total worker-types running this suite")
lines.append("")

# OS row
os_labels = [classify_os(wt) for wt in all_wts]
lines.append(f"| OS | {'|'.join(os_labels)} | |")

# Header
header = "| Suite | " + " | ".join(short_wts) + " | # |"
lines.append(header)
sep = "| :--- | " + " | ".join([":---:" for _ in all_wts]) + " | ---: |"
lines.append(sep)

def emit_rows(suite_list):
    for suite_name, count in suite_list:
        wts_for_suite = suite_wts.get(suite_name, set())
        cells = []
        for wt in all_wts:
            cells.append("`*`" if wt in wts_for_suite else " ")
        risk = f"**{count}**" if count <= 1 else str(count)
        lines.append(f"| {suite_name} | " + " | ".join(cells) + f" | {risk} |")

# Performance section
lines.append(f"| **--- Performance ({len(groups['perf'])} suites) ---** | " + " | ".join(["" for _ in all_wts]) + " | |")
emit_rows(groups["perf"])

# Functional section
lines.append(f"| **--- Functional ({len(groups['func'])} suites) ---** | " + " | ".join(["" for _ in all_wts]) + " | |")
emit_rows(groups["func"])

# Other section
lines.append(f"| **--- Other / AWSY ({len(groups['other'])} suites) ---** | " + " | ".join(["" for _ in all_wts]) + " | |")
emit_rows(groups["other"])

out = BASE / "history" / "2026-03-31_suite_matrix.md"
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Markdown matrix saved to: {out}")
print(f"  {len(all_suites)} suites x {len(all_wts)} worker-types")
