"""
Generate a pool-centric diagram showing fxci-config pools and
which test suites are assigned to each.

Uses coverage_map.json data and maps worker-types to actual pool IDs.
"""

import json
import yaml
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

BASE = Path(__file__).parent

# Load coverage map
with open(BASE / "coverage_map.json") as f:
    cov_data = json.load(f)

# Load pool definitions
with open(BASE / "fxci-config" / "worker-pools.yml") as f:
    pools_raw = yaml.safe_load(f)

# Expand pool definitions
pools = {}
for pool_entry in pools_raw.get("pools", []):
    pool_id = pool_entry.get("pool_id", "")
    variants = pool_entry.get("variants", [])
    provider = pool_entry.get("provider_id", "")
    if isinstance(provider, dict):
        provider = str(provider)

    if variants:
        for variant in variants:
            expanded_id = pool_id
            for key, val in variant.items():
                expanded_id = expanded_id.replace(f"{{{key}}}", str(val))
            expanded_id = re.sub(r'\{[^}]*\}', '', expanded_id)
            pools[expanded_id] = {"provider": provider, "is_alpha": "alpha" in expanded_id.lower()}
    else:
        pools[pool_id] = {"provider": provider, "is_alpha": "alpha" in pool_id.lower()}

# Map worker-types to pool IDs
# Worker-types are the short name; pool IDs include the pool-group prefix (e.g., gecko-t/)
wt_to_pools = {}
for pool_id in pools:
    # Extract the worker-type portion (after the /)
    if "/" in pool_id:
        wt_part = pool_id.split("/", 1)[1]
    else:
        wt_part = pool_id
    if wt_part not in wt_to_pools:
        wt_to_pools[wt_part] = []
    wt_to_pools[wt_part].append(pool_id)

# Build the pool -> suite mapping from coverage data
wt_coverage = cov_data["worker_type_coverage"]

# For the diagram, focus on tester pools (gecko-t/) and map suites
pool_suites = {}
for wt, info in wt_coverage.items():
    # Find matching pool(s)
    matching_pools = wt_to_pools.get(wt, [])
    # Also try common prefixes
    if not matching_pools:
        for pool_wt, pool_list in wt_to_pools.items():
            if pool_wt.startswith(wt) or wt.startswith(pool_wt):
                matching_pools.extend(pool_list)

    pool_suites[wt] = {
        "pool_ids": matching_pools,
        "pool_id_display": matching_pools[0] if matching_pools else f"(no pool found: {wt})",
        "suites": info["suites"],
        "suite_count": info["suite_count"],
        "perf_count": len(info.get("perf_suites", [])),
        "func_count": len(info.get("functional_suites", [])),
        "other_count": info["suite_count"] - len(info.get("perf_suites", [])) - len(info.get("functional_suites", [])),
        "platforms": info["platforms"],
    }


def classify_os(wt, platforms):
    sample = platforms[0] if platforms else wt
    if "linux" in sample or "linux" in wt:
        return "Linux"
    elif "win" in sample or "win" in wt:
        return "Windows"
    elif "macosx" in sample or "osx" in wt:
        return "macOS"
    elif "android" in sample or "bitbar" in wt or "lambda" in wt:
        return "Android"
    return "Other"


# Categorize
os_groups = {"Linux": [], "Windows": [], "macOS": [], "Android": []}
for wt, info in sorted(pool_suites.items(), key=lambda x: -x[1]["suite_count"]):
    os_name = classify_os(wt, info["platforms"])
    os_groups[os_name].append((wt, info))

# Colors
OS_COLORS = {"Linux": "#4A90D9", "Windows": "#7B68EE", "macOS": "#E88D39", "Android": "#50C878"}
PERF_COLOR = "#E74C3C"
FUNC_COLOR = "#3498DB"
OTHER_COLOR = "#95A5A6"

# --- Create the figure ---
fig = plt.figure(figsize=(26, 20), facecolor="#1a1a2e")
fig.suptitle("Firefox CI: Worker Pools & Test Suite Assignments", fontsize=24,
             fontweight="bold", color="white", y=0.97)
fig.text(0.5, 0.945,
         "Y-axis = worker-type (maps to gecko-t/ pool)  |  Bar length = # of test suites assigned  |  Labels show pool ID + suite/platform counts",
         ha="center", fontsize=11, color="#aaaaaa")

from matplotlib.gridspec import GridSpec
gs = GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35,
              left=0.18, right=0.92, top=0.91, bottom=0.06)

for idx, (os_name, entries) in enumerate(os_groups.items()):
    ax = fig.add_subplot(gs[idx // 2, idx % 2])
    ax.set_facecolor("#16213e")

    if not entries:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white", fontsize=14)
        ax.set_title(os_name, fontsize=18, fontweight="bold", color=OS_COLORS[os_name], pad=12)
        continue

    labels = []
    perf_counts = []
    func_counts = []
    other_counts = []
    annotations = []

    for wt, info in entries:
        # Build label: pool display name
        pool_display = info["pool_id_display"]
        if pool_display.startswith("(no pool"):
            pool_display = wt
        elif "/" in pool_display:
            pool_display = pool_display.split("/", 1)[1]

        labels.append(pool_display)
        perf_counts.append(info["perf_count"])
        func_counts.append(info["func_count"])
        other_counts.append(info["other_count"])
        annotations.append(f"{info['suite_count']} suites / {len(info['platforms'])} platforms")

    y_pos = np.arange(len(labels))
    bar_height = 0.65

    ax.barh(y_pos, perf_counts, bar_height, color=PERF_COLOR, alpha=0.85, label="Perf")
    ax.barh(y_pos, func_counts, bar_height, left=perf_counts, color=FUNC_COLOR, alpha=0.85, label="Functional")
    left_other = [p + f for p, f in zip(perf_counts, func_counts)]
    ax.barh(y_pos, other_counts, bar_height, left=left_other, color=OTHER_COLOR, alpha=0.85, label="Other")

    # Annotations
    for i, ann in enumerate(annotations):
        total = perf_counts[i] + func_counts[i] + other_counts[i]
        ax.text(total + 0.8, i, ann, va="center", fontsize=8.5, color="#cccccc")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.5, color="white", fontfamily="monospace")
    ax.invert_yaxis()
    ax.set_xlabel("Number of Suites", fontsize=10, color="#aaaaaa")
    unique_platforms = set()
    for _, e in entries:
        unique_platforms.update(e["platforms"])
    ax.set_title(f"{os_name}  ({len(unique_platforms)} test platforms)",
                 fontsize=18, fontweight="bold", color=OS_COLORS[os_name], pad=12)
    ax.tick_params(colors="#aaaaaa")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")

    max_total = max(p + f + o for p, f, o in zip(perf_counts, func_counts, other_counts))
    ax.set_xlim(0, max_total * 1.55)

# Legend
legend_elements = [
    mpatches.Patch(facecolor=PERF_COLOR, alpha=0.85, label="Performance (Talos/Browsertime)"),
    mpatches.Patch(facecolor=FUNC_COLOR, alpha=0.85, label="Functional (Mochitest/WPT/xpcshell/etc)"),
    mpatches.Patch(facecolor=OTHER_COLOR, alpha=0.85, label="Other (AWSY memory tests)"),
]
fig.legend(handles=legend_elements, loc="lower center", ncol=3,
           fontsize=12, facecolor="#1a1a2e", edgecolor="#444444",
           labelcolor="white", framealpha=0.9)

out_path = BASE / "pool_coverage_diagram.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Pool diagram saved to: {out_path}")
