"""
Generate two coverage diagrams:
  1. Worker-type view: worker-types on y-axis, suite counts as bars
  2. Test platform view: every test platform on y-axis, suite counts as bars
"""

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

BASE = Path(__file__).parent.parent

with open(BASE / "docs" / "coverage_map.json") as f:
    cov_data = json.load(f)

wt_data = cov_data["worker_type_coverage"]
plat_data = cov_data["platform_details"]

OS_COLORS = {"Linux": "#4A90D9", "Windows": "#7B68EE", "macOS": "#E88D39", "Android": "#50C878"}
PERF_COLOR = "#E74C3C"
FUNC_COLOR = "#3498DB"
OTHER_COLOR = "#95A5A6"

PERF_PREFIXES = ("talos-", "browsertime-")
OTHER_PREFIXES = ("awsy",)


def classify_os(name):
    if "linux" in name: return "Linux"
    elif "win" in name: return "Windows"
    elif "macosx" in name or "osx" in name: return "macOS"
    elif "android" in name or "bitbar" in name or "lambda" in name: return "Android"
    return "Other"


def classify_suite(s):
    if any(s.startswith(p) for p in PERF_PREFIXES): return "perf"
    if any(s.startswith(p) for p in OTHER_PREFIXES): return "other"
    return "func"


def make_chart(ax, labels, perf, func, other, annotations, os_name, title_count, title_unit):
    ax.set_facecolor("#16213e")
    if not labels:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", color="white")
        ax.set_title(f"{os_name}", fontsize=16, fontweight="bold", color=OS_COLORS[os_name])
        return

    y = np.arange(len(labels))
    h = min(0.7, 8.0 / max(len(labels), 1))

    ax.barh(y, perf, h, color=PERF_COLOR, alpha=0.85)
    ax.barh(y, func, h, left=perf, color=FUNC_COLOR, alpha=0.85)
    left_o = [p + f for p, f in zip(perf, func)]
    ax.barh(y, other, h, left=left_o, color=OTHER_COLOR, alpha=0.85)

    for i, ann in enumerate(annotations):
        total = perf[i] + func[i] + other[i]
        ax.text(total + 0.8, i, ann, va="center", fontsize=7, color="#cccccc")

    ax.set_yticks(y)
    fs = 8 if len(labels) > 15 else 9
    ax.set_yticklabels(labels, fontsize=fs, color="white", fontfamily="monospace")
    ax.invert_yaxis()
    ax.set_xlabel("Suites", fontsize=9, color="#aaaaaa")
    ax.set_title(f"{os_name}  ({title_count} {title_unit})",
                 fontsize=16, fontweight="bold", color=OS_COLORS[os_name], pad=10)
    ax.tick_params(colors="#aaaaaa")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")
    max_t = max(p + f + o for p, f, o in zip(perf, func, other))
    ax.set_xlim(0, max_t * 1.5)


# ============================================================
# DIAGRAM 1: Worker-type view
# ============================================================
def gen_worker_type_diagram():
    os_groups = {"Linux": [], "Windows": [], "macOS": [], "Android": []}
    for wt, info in sorted(wt_data.items(), key=lambda x: -x[1]["suite_count"]):
        os_name = classify_os(wt if "osx" in wt or "bitbar" in wt or "lambda" in wt
                              else (info["platforms"][0] if info["platforms"] else wt))
        os_groups[os_name].append((wt, info))

    fig = plt.figure(figsize=(26, 18), facecolor="#1a1a2e")
    fig.suptitle("Firefox CI Coverage: Worker-Types", fontsize=24, fontweight="bold",
                 color="white", y=0.97)
    fig.text(0.5, 0.945, "Y-axis = worker-type (pool)  |  Bar = # test suites assigned",
             ha="center", fontsize=11, color="#aaaaaa")

    from matplotlib.gridspec import GridSpec
    gs = GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35,
                  left=0.18, right=0.92, top=0.91, bottom=0.06)

    for idx, (os_name, entries) in enumerate(os_groups.items()):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])
        labels, perf, func, other, anns = [], [], [], [], []
        for wt, info in entries:
            labels.append(wt)
            p = len(info.get("perf_suites", []))
            f = len(info.get("functional_suites", []))
            o = info["suite_count"] - p - f
            perf.append(p); func.append(f); other.append(o)
            anns.append(f"{info['suite_count']} suites")
        make_chart(ax, labels, perf, func, other, anns, os_name, len(entries), "worker-types")

    legend_elements = [
        mpatches.Patch(facecolor=PERF_COLOR, alpha=0.85, label="Performance (Talos/Browsertime)"),
        mpatches.Patch(facecolor=FUNC_COLOR, alpha=0.85, label="Functional (Mochitest/WPT/xpcshell/etc)"),
        mpatches.Patch(facecolor=OTHER_COLOR, alpha=0.85, label="Other (AWSY)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=3, fontsize=11,
               facecolor="#1a1a2e", edgecolor="#444444", labelcolor="white", framealpha=0.9)

    out = BASE / "docs" / "diagram_worker_types.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Worker-type diagram saved to: {out}")


# ============================================================
# DIAGRAM 2: Test platform view
# ============================================================
def gen_test_platform_diagram():
    os_groups = {"Linux": [], "Windows": [], "macOS": [], "Android": []}
    for pname, info in sorted(plat_data.items()):
        os_name = info["os_family"]
        suites = info["suites"]
        p = sum(1 for s in suites if classify_suite(s) == "perf")
        f = sum(1 for s in suites if classify_suite(s) == "func")
        o = len(suites) - p - f
        os_groups[os_name].append((pname, suites, p, f, o))

    # Calculate figure height based on max entries
    max_entries = max(len(v) for v in os_groups.values())
    fig_height = max(18, max_entries * 0.45 + 4)

    fig = plt.figure(figsize=(28, fig_height), facecolor="#1a1a2e")
    fig.suptitle("Firefox CI Coverage: Test Platforms", fontsize=24, fontweight="bold",
                 color="white", y=0.98)
    fig.text(0.5, 0.97, "Y-axis = test platform  |  Bar = # test suites assigned",
             ha="center", fontsize=11, color="#aaaaaa")

    from matplotlib.gridspec import GridSpec
    gs = GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35,
                  left=0.22, right=0.92, top=0.95, bottom=0.04)

    for idx, (os_name, entries) in enumerate(os_groups.items()):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])
        # Sort by suite count descending
        entries = sorted(entries, key=lambda x: -(x[2] + x[3] + x[4]))
        labels = [e[0] for e in entries]
        perf = [e[2] for e in entries]
        func = [e[3] for e in entries]
        other = [e[4] for e in entries]
        anns = [f"{e[2]+e[3]+e[4]} suites" for e in entries]
        make_chart(ax, labels, perf, func, other, anns, os_name, len(entries), "test platforms")

    legend_elements = [
        mpatches.Patch(facecolor=PERF_COLOR, alpha=0.85, label="Performance (Talos/Browsertime)"),
        mpatches.Patch(facecolor=FUNC_COLOR, alpha=0.85, label="Functional (Mochitest/WPT/xpcshell/etc)"),
        mpatches.Patch(facecolor=OTHER_COLOR, alpha=0.85, label="Other (AWSY)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=3, fontsize=11,
               facecolor="#1a1a2e", edgecolor="#444444", labelcolor="white", framealpha=0.9)

    out = BASE / "docs" / "diagram_test_platforms.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Test platform diagram saved to: {out}")


if __name__ == "__main__":
    gen_worker_type_diagram()
    gen_test_platform_diagram()
