"""
Generate a matrix diagram: suites (rows) x worker-types (columns).
A filled dot means the suite runs on that worker-type.
"""

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

BASE = Path(__file__).parent.parent

with open(BASE / "docs" / "coverage_map.json") as f:
    cov_data = json.load(f)

wt_data = cov_data["worker_type_coverage"]


def classify_os(name):
    if "linux" in name: return "Linux"
    elif "win" in name: return "Windows"
    elif "osx" in name: return "macOS"
    elif "bitbar" in name or "lambda" in name or "kvm" in name: return "Android"
    return "Other"


# Build suite -> worker-type presence map
suite_to_wt = {}
all_wts = sorted(wt_data.keys())
all_suites = set()
for wt, info in wt_data.items():
    for s in info["suites"]:
        all_suites.add(s)
        if s not in suite_to_wt:
            suite_to_wt[s] = set()
        suite_to_wt[s].add(wt)

all_suites = sorted(all_suites)

# Order worker-types by OS group for readability
os_order = {"Linux": 0, "Windows": 1, "macOS": 2, "Android": 3, "Other": 4}
all_wts = sorted(all_wts, key=lambda w: (os_order.get(classify_os(w), 4), w))

# Build the matrix
matrix = np.zeros((len(all_suites), len(all_wts)), dtype=int)
for i, suite in enumerate(all_suites):
    for j, wt in enumerate(all_wts):
        if wt in suite_to_wt.get(suite, set()):
            matrix[i, j] = 1

# Color dots by OS
OS_COLORS = {"Linux": "#4A90D9", "Windows": "#7B68EE", "macOS": "#E88D39", "Android": "#50C878"}
wt_colors = [OS_COLORS.get(classify_os(wt), "#888888") for wt in all_wts]

# Figure sizing
n_suites = len(all_suites)
n_wts = len(all_wts)
cell_w = 0.45
cell_h = 0.28
fig_w = max(16, 6 + n_wts * cell_w)
fig_h = max(20, 3 + n_suites * cell_h)

fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="#1a1a2e")
ax.set_facecolor("#16213e")

fig.suptitle("Firefox CI: Suite x Worker-Type Matrix",
             fontsize=20, fontweight="bold", color="white", y=0.995)

# Draw dots
for i in range(n_suites):
    for j in range(n_wts):
        if matrix[i, j]:
            ax.plot(j, i, 'o', color=wt_colors[j], markersize=7, alpha=0.9)

# Grid lines
for i in range(n_suites + 1):
    ax.axhline(i - 0.5, color="#2a2a4a", linewidth=0.3)
for j in range(n_wts + 1):
    ax.axvline(j - 0.5, color="#2a2a4a", linewidth=0.3)

# Alternate row shading
for i in range(n_suites):
    if i % 2 == 0:
        ax.axhspan(i - 0.5, i + 0.5, color="#1e2a4a", alpha=0.4)

# OS group separators and headers along top
prev_os = None
os_spans = []
for j, wt in enumerate(all_wts):
    os_name = classify_os(wt)
    if os_name != prev_os:
        if prev_os is not None:
            ax.axvline(j - 0.5, color="#555555", linewidth=1.5)
        os_spans.append((j, os_name))
        prev_os = os_name

# Draw OS group labels above the worker-type labels
for idx, (start_j, os_name) in enumerate(os_spans):
    end_j = os_spans[idx + 1][0] if idx + 1 < len(os_spans) else n_wts
    mid = (start_j + end_j - 1) / 2
    ax.text(mid, -2.8, os_name, ha="center", va="bottom",
            fontsize=11, fontweight="bold", color=OS_COLORS.get(os_name, "white"))

# Coverage count on right side
for i, suite in enumerate(all_suites):
    count = int(matrix[i].sum())
    ax.text(n_wts + 0.3, i, str(count), va="center", fontsize=7, color="#aaaaaa")
ax.text(n_wts + 0.3, -1.5, "#", va="center", fontsize=8, fontweight="bold", color="#aaaaaa")

# Axes
ax.set_xlim(-0.5, n_wts + 1)
ax.set_ylim(n_suites - 0.5, -1.5)

ax.set_xticks(range(n_wts))
ax.set_xticklabels(all_wts, rotation=55, ha="right", fontsize=7.5, color="white", fontfamily="monospace")

ax.set_yticks(range(n_suites))
ax.set_yticklabels(all_suites, fontsize=7, color="white", fontfamily="monospace")

ax.tick_params(axis='both', which='both', length=0)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.spines["left"].set_visible(False)

plt.subplots_adjust(left=0.22, right=0.95, top=0.96, bottom=0.08)

out = BASE / "docs" / "diagram_suite_matrix.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Matrix diagram saved to: {out}")
print(f"  {n_suites} suites x {n_wts} worker-types")
