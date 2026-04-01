"""
Generate a visual coverage diagram from coverage_map.json.
"""

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
from pathlib import Path

BASE = Path(__file__).parent

with open(BASE / "coverage_map.json") as f:
    data = json.load(f)

wt_data = data["worker_type_coverage"]

# Categorize worker-types by OS
os_groups = {"Linux": [], "Windows": [], "macOS": [], "Android": []}
for wt, info in sorted(wt_data.items()):
    platforms = info["platforms"]
    sample = platforms[0] if platforms else wt
    if "linux" in sample or "linux" in wt:
        os_groups["Linux"].append((wt, info))
    elif "win" in sample or "win" in wt:
        os_groups["Windows"].append((wt, info))
    elif "macosx" in sample or "osx" in wt:
        os_groups["macOS"].append((wt, info))
    elif "android" in sample or "bitbar" in wt or "lambda" in wt:
        os_groups["Android"].append((wt, info))
    else:
        os_groups["Linux"].append((wt, info))

# Color scheme
OS_COLORS = {
    "Linux": "#4A90D9",
    "Windows": "#7B68EE",
    "macOS": "#E88D39",
    "Android": "#50C878",
}
PERF_COLOR = "#E74C3C"
FUNC_COLOR = "#3498DB"
OTHER_COLOR = "#95A5A6"

fig = plt.figure(figsize=(24, 18), facecolor="#1a1a2e")
fig.suptitle("Firefox CI Test Coverage Map", fontsize=24, fontweight="bold",
             color="white", y=0.97)
fig.text(0.5, 0.95, "Suites per worker-type  |  Y-axis = worker-type (pool name)  |  Bar = suite count by category",
         ha="center", fontsize=12, color="#aaaaaa")

gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3,
              left=0.06, right=0.94, top=0.91, bottom=0.06)

for idx, (os_name, entries) in enumerate(os_groups.items()):
    ax = fig.add_subplot(gs[idx // 2, idx % 2])
    ax.set_facecolor("#16213e")

    if not entries:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.set_title(os_name, fontsize=16, fontweight="bold", color=OS_COLORS[os_name], pad=10)
        continue

    # Sort by total suite count descending
    entries = sorted(entries, key=lambda x: x[1]["suite_count"], reverse=True)

    labels = []
    perf_counts = []
    func_counts = []
    other_counts = []
    platform_counts = []

    for wt, info in entries:
        # Shorten worker-type name for display
        short = wt.replace("t-linux-docker-noscratch-", "docker-noscratch-")
        short = short.replace("t-linux-docker-", "docker-")
        short = short.replace("t-linux-", "linux-")
        short = short.replace("t-osx-", "osx-")
        short = short.replace("t-bitbar-gw-unit-", "bitbar-")
        short = short.replace("t-lambda-perf-", "lambda-")
        is_alpha = "alpha" in wt.lower()
        if is_alpha:
            short += " *"
        labels.append(short)
        perf_counts.append(len(info.get("perf_suites", [])))
        func_counts.append(len(info.get("functional_suites", [])))
        other_counts.append(info["suite_count"] - len(info.get("perf_suites", [])) - len(info.get("functional_suites", [])))
        platform_counts.append(info["platform_count"])

    y_pos = np.arange(len(labels))
    bar_height = 0.6

    bars_perf = ax.barh(y_pos, perf_counts, bar_height, color=PERF_COLOR, alpha=0.85, label="Performance")
    bars_func = ax.barh(y_pos, func_counts, bar_height, left=perf_counts, color=FUNC_COLOR, alpha=0.85, label="Functional")
    left_other = [p + f for p, f in zip(perf_counts, func_counts)]
    bars_other = ax.barh(y_pos, other_counts, bar_height, left=left_other, color=OTHER_COLOR, alpha=0.85, label="Other (AWSY)")

    # Add total count labels
    for i, (p, f, o, pc) in enumerate(zip(perf_counts, func_counts, other_counts, platform_counts)):
        total = p + f + o
        ax.text(total + 1, i, f"{total} suites / {pc} plat",
                va="center", fontsize=8, color="#cccccc")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9, color="white")
    ax.invert_yaxis()
    ax.set_xlabel("Number of Suites", fontsize=10, color="#aaaaaa")
    ax.set_title(os_name, fontsize=16, fontweight="bold", color=OS_COLORS[os_name], pad=10)
    ax.tick_params(colors="#aaaaaa")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")

    # Set x-axis limit with padding for labels
    max_total = max(p + f + o for p, f, o in zip(perf_counts, func_counts, other_counts))
    ax.set_xlim(0, max_total * 1.45)

# Legend
legend_elements = [
    mpatches.Patch(facecolor=PERF_COLOR, alpha=0.85, label="Performance (Talos/Browsertime)"),
    mpatches.Patch(facecolor=FUNC_COLOR, alpha=0.85, label="Functional (Mochitest/WPT/etc)"),
    mpatches.Patch(facecolor=OTHER_COLOR, alpha=0.85, label="Other (AWSY)"),
]
fig.legend(handles=legend_elements, loc="lower center", ncol=3,
           fontsize=11, facecolor="#1a1a2e", edgecolor="#444444",
           labelcolor="white", framealpha=0.9)

out_path = BASE / "coverage_map_diagram.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Diagram saved to: {out_path}")
