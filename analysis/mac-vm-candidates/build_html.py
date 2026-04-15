"""
Build an HTML page showing macOS functional test suites categorized by
VM migration feasibility for Tart on Mac Minis.
"""

import json
import yaml
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent.parent
FIREFOX = BASE / "firefox"
TC = FIREFOX / "taskcluster"
ANALYSIS = BASE / "analysis"

TIER_1_PLATFORMS = json.loads(
    (ANALYSIS / "tier_matrix.json").read_text(encoding="utf-8")
).get("tier_1_platforms", [])
TIER_1_SET = set(TIER_1_PLATFORMS)

PERF_PREFIXES = ["talos-", "browsertime-", "awsy"]

WORKER_MAP = {
    "macosx1015-64": {"worker": "t-osx-1015-r8", "arch": "Intel", "os_ver": "10.15"},
    "macosx1470-64": {"worker": "t-osx-1400-r8", "arch": "Intel", "os_ver": "14.70"},
    "macosx1400-64": {"worker": "t-osx-1400-m2", "arch": "Apple Silicon", "os_ver": "14.00"},
    "macosx1500-64": {"worker": "t-osx-1500-m4", "arch": "Apple Silicon", "os_ver": "15.00"},
    "macosx1500-aarch64": {"worker": "t-osx-1500-m4", "arch": "Apple Silicon", "os_ver": "15.00"},
}


def get_mac_platforms():
    tp = yaml.safe_load((TC / "test_configs/test-platforms.yml").read_text(encoding="utf-8"))
    return {k: v for k, v in tp.items() if k.startswith("macosx")}


def expand_test_sets(set_names):
    ts = yaml.safe_load((TC / "test_configs/test-sets.yml").read_text(encoding="utf-8"))
    suites = set()
    for name in set_names:
        if name in ts and isinstance(ts[name], list):
            suites.update(ts[name])
    return suites


def get_suite_properties():
    """Get virtualization, instance-size, etc. from kind YAMLs."""
    props = {}
    kind_dir = TC / "kinds" / "test"
    for yml_file in kind_dir.glob("*.yml"):
        if yml_file.name == "kind.yml":
            continue
        try:
            data = yaml.safe_load(yml_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        defaults = data.get("task-defaults", {})
        for name, defn in data.items():
            if name == "task-defaults" or not isinstance(defn, dict):
                continue
            props[name] = {
                "virtualization": defn.get("virtualization", defaults.get("virtualization", "virtual")),
                "instance_size": defn.get("instance-size", defaults.get("instance-size", "default")),
                "max_run_time": defn.get("max-run-time", defaults.get("max-run-time", 3600)),
                "loopback_video": defn.get("loopback-video", defaults.get("loopback-video", False)),
                "allow_sw_gl": defn.get("allow-software-gl-layers", defaults.get("allow-software-gl-layers", True)),
            }
    return props


def classify_suite(name, props):
    """Classify a suite into high/medium/low VM likelihood."""
    p = props.get(name, {})
    virt = p.get("virtualization", "virtual")
    inst = p.get("instance_size", "default")
    video = p.get("loopback_video", False)
    sw_gl = p.get("allow_sw_gl", True)
    mrt = p.get("max_run_time", 3600)

    # Performance suites — not candidates
    if any(name.startswith(pf) for pf in PERF_PREFIXES):
        return "perf", "Performance suite — bare metal required"

    # Explicit hardware virtualization
    if virt == "hardware":
        return "perf", "Explicit hardware virtualization"

    reasons = []

    # Check for GPU/graphics indicators
    gpu_keywords = ["gpu", "webgl", "webgpu"]
    graphics_keywords = ["reftest", "canvas", "screenshot"]
    media_keywords = ["media", "webcodecs", "eme"]

    has_gpu = any(k in name.lower() for k in gpu_keywords)
    has_graphics = any(k in name.lower() for k in graphics_keywords)
    has_media = any(k in name.lower() for k in media_keywords)

    # Check resource heaviness
    is_heavy = False
    if isinstance(inst, str) and ("large" in inst.lower() or "high" in inst.lower()):
        is_heavy = True
    if isinstance(inst, dict):
        # keyed-by — check for highcpu/large in values
        for v in str(inst).lower().split():
            if "highcpu" in v or "large" in v:
                is_heavy = True

    needs_video = video
    needs_hw_gl = (sw_gl == False)
    long_runtime = isinstance(mrt, int) and mrt > 7200

    # Classification logic
    if is_heavy:
        reasons.append(f"Heavy resources (instance-size: {inst})")
        if needs_video:
            reasons.append("Requires loopback video")
        return "low", "; ".join(reasons)

    if needs_video and needs_hw_gl:
        reasons.append("Requires loopback video + hardware GL")
        return "low", "; ".join(reasons)

    if has_gpu:
        reasons.append("GPU-dependent (WebGL/WebGPU)")
        if needs_hw_gl:
            reasons.append("Disables software GL")
        return "medium", "; ".join(reasons)

    if has_graphics:
        reasons.append("Graphics/rendering comparison")
        return "medium", "; ".join(reasons)

    if has_media:
        reasons.append("Media playback/encoding")
        return "medium", "; ".join(reasons)

    if needs_video:
        reasons.append("Requires loopback video")
        return "medium", "; ".join(reasons)

    if long_runtime:
        reasons.append(f"Long runtime ({mrt}s)")
        return "medium", "; ".join(reasons)

    # Default: virtual on other platforms, no flags
    reasons.append("Virtual on Linux/Windows, default resources, no GPU/video needs")
    return "high", "; ".join(reasons)


def main():
    print("Building macOS VM candidates HTML...")

    tier_data = json.loads((ANALYSIS / "tier_matrix.json").read_text(encoding="utf-8"))
    skip_data = json.loads((ANALYSIS / "tier_skip_crossref.json").read_text(encoding="utf-8"))
    mac_plats = tier_data["platforms_by_os"].get("macOS", [])
    mac_t1_plats = [p for p in mac_plats if p in TIER_1_SET]
    matrix = tier_data["matrix"]

    mac_platforms = get_mac_platforms()
    suite_props = get_suite_properties()

    # Collect all functional suites that run on macOS
    mac_suites = set()
    for plat_name, plat_def in mac_platforms.items():
        test_set_names = plat_def.get("test-sets", [])
        mac_suites.update(expand_test_sets(test_set_names))

    # Classify each suite
    classified = []
    for suite in sorted(mac_suites):
        likelihood, reason = classify_suite(suite, suite_props)

        # Tier info
        is_t1 = any(matrix.get(suite, {}).get(p) == 1 for p in mac_t1_plats)

        # Skip info
        skip_info = skip_data.get("suites", {}).get(suite, {})
        skipped = skip_info.get("total_skipped", 0)
        skipped_all = skip_info.get("skipped_all_platforms", 0)

        # Which platforms does it actually run on?
        runs_on = []
        for plat_name, plat_def in mac_platforms.items():
            plat_suites = expand_test_sets(plat_def.get("test-sets", []))
            if suite in plat_suites:
                hw = None
                for base, info in WORKER_MAP.items():
                    if plat_name.startswith(base):
                        hw = info
                        break
                runs_on.append({
                    "platform": plat_name,
                    "arch": hw["arch"] if hw else "?",
                })

        archs = set(r["arch"] for r in runs_on)
        arch_str = " + ".join(sorted(archs)) if archs else "?"

        classified.append({
            "suite": suite,
            "likelihood": likelihood,
            "reason": reason,
            "tier": 1 if is_t1 else 2,
            "skipped": skipped,
            "skipped_all": skipped_all,
            "arch": arch_str,
            "platform_count": len(runs_on),
        })

    # Build HTML
    html = build_html(classified)
    out = BASE / "docs" / "mac_vm_candidates.html"
    out.write_text(html, encoding="utf-8")
    print(f"  HTML saved to: {out}")

    # Stats
    high = [c for c in classified if c["likelihood"] == "high"]
    med = [c for c in classified if c["likelihood"] == "medium"]
    low = [c for c in classified if c["likelihood"] == "low"]
    perf = [c for c in classified if c["likelihood"] == "perf"]
    print(f"  High: {len(high)}, Medium: {len(med)}, Low: {len(low)}, Perf (excluded): {len(perf)}")


def build_html(classified):
    high = [c for c in classified if c["likelihood"] == "high"]
    med = [c for c in classified if c["likelihood"] == "medium"]
    low = [c for c in classified if c["likelihood"] == "low"]
    perf = [c for c in classified if c["likelihood"] == "perf"]

    total_functional = len(high) + len(med) + len(low)
    high_t1 = sum(1 for c in high if c["tier"] == 1)
    med_t1 = sum(1 for c in med if c["tier"] == 1)
    low_t1 = sum(1 for c in low if c["tier"] == 1)

    def make_rows(items):
        rows = []
        for c in sorted(items, key=lambda x: (-x["tier"], x["suite"])):
            tier_cls = "tier-1" if c["tier"] == 1 else "tier-2"
            tier_label = "T1" if c["tier"] == 1 else "T2+"
            skip_cls = "skip-warn" if c["skipped"] > 50 else "skip-ok" if c["skipped"] > 0 else ""
            rows.append(
                f'<tr>'
                f'<td class="suite-name">{c["suite"]}</td>'
                f'<td class="{tier_cls}">{tier_label}</td>'
                f'<td class="arch">{c["arch"]}</td>'
                f'<td class="{skip_cls}">{c["skipped"]}</td>'
                f'<td>{c["skipped_all"]}</td>'
                f'<td class="reason">{c["reason"]}</td>'
                f'</tr>'
            )
        return "\n".join(rows)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>macOS VM Migration Candidates</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: #1a1a2e;
    color: #ccc;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}}
.top-bar {{
    position: sticky;
    top: 0;
    z-index: 200;
    background: #0d1525;
    padding: 12px 20px;
    border-bottom: 2px solid #333;
}}
.top-bar h1 {{ color: white; font-size: 20px; margin-bottom: 4px; }}
.top-bar .subtitle {{ color: #888; font-size: 12px; margin-bottom: 10px; }}
.stats {{
    display: flex;
    gap: 20px;
    margin-bottom: 8px;
    font-size: 12px;
    flex-wrap: wrap;
}}
.stat {{ color: #aaa; }}
.stat b {{ color: white; }}
.stat-high b {{ color: #27AE60; }}
.stat-med b {{ color: #F39C12; }}
.stat-low b {{ color: #E74C3C; }}
.legend {{
    display: flex;
    gap: 18px;
    font-size: 12px;
    margin-bottom: 8px;
}}
.legend span {{ display: flex; align-items: center; gap: 5px; }}
.swatch {{ width: 14px; height: 14px; display: inline-block; border-radius: 2px; }}
.swatch-high {{ background: #27AE60; }}
.swatch-med {{ background: #F39C12; }}
.swatch-low {{ background: #E74C3C; }}
.swatch-perf {{ background: #555; }}
.nav-bar {{
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
}}
.nav-link {{
    color: #ccc;
    text-decoration: none;
    padding: 4px 12px;
    border-radius: 4px;
    background: #16213e;
    font-size: 12px;
    border-left: 3px solid;
}}
.nav-link:hover {{ background: #2a3a5a; }}
.content {{
    padding: 16px 20px;
    max-width: 1200px;
}}
.section {{
    margin-bottom: 30px;
}}
.section-header {{
    padding: 10px 12px 6px 12px;
    margin-bottom: 0;
    background: #0d1525;
    border-radius: 4px 4px 0 0;
    position: sticky;
    top: 153px;
    z-index: 50;
    box-shadow: 0 -4px 0 0 #1a1a2e;
}}
.section-header h2 {{ font-size: 16px; display: inline; margin-right: 12px; }}
.section-stats {{ color: #888; font-size: 12px; }}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 0;
}}
thead th {{
    position: sticky;
    top: 186px;
    z-index: 40;
    background: #0d1525;
    padding: 4px 8px 6px 8px;
    font-size: 11px;
    color: #aaa;
    text-align: left;
    border-bottom: 1px solid #444;
    box-shadow: 0 -2px 0 0 #0d1525;
}}
th.center {{ text-align: center; }}
td {{
    padding: 4px 8px;
    border-bottom: 1px solid #1e2a4a;
    font-size: 12px;
}}
.suite-name {{ color: #ddd; white-space: nowrap; }}
.tier-1 {{ color: #27AE60; font-weight: bold; text-align: center; }}
.tier-2 {{ color: #F39C12; text-align: center; }}
.arch {{ color: #aaa; font-size: 11px; text-align: center; }}
.skip-warn {{ color: #F39C12; text-align: center; }}
.skip-ok {{ color: #888; text-align: center; }}
.reason {{ color: #888; font-size: 11px; }}
tr:nth-child(even) {{ background: #1a1a2e; }}
tr:nth-child(odd) {{ background: #16213e; }}
tr:hover {{ background: #2a3a5a !important; }}
.context-box {{
    margin-top: 30px;
    padding: 16px;
    background: #0d1525;
    border-radius: 6px;
    border: 1px solid #333;
}}
.context-box h2 {{ color: white; font-size: 16px; margin-bottom: 10px; }}
.context-box p {{ color: #999; font-size: 12px; line-height: 1.6; margin-bottom: 8px; }}
.context-box ul {{ color: #999; font-size: 12px; line-height: 1.8; margin-left: 20px; }}
</style>
</head>
<body>

<div class="top-bar">
    <h1>macOS VM Migration Candidates</h1>
    <p class="subtitle">Which macOS functional test suites can move from bare metal to Tart VMs on Mac Minis (16GB, 2 VMs/host)?</p>
    <div class="stats">
        <span class="stat">All macOS suites: <b>{len(classified)}</b></span>
        <span class="stat">Performance (bare metal): <b>{len(perf)}</b></span>
        <span class="stat">Functional: <b>{total_functional}</b></span>
        <span class="stat stat-high">High likelihood VM: <b>{len(high)}</b> ({high_t1} T1)</span>
        <span class="stat stat-med">Medium (investigate): <b>{len(med)}</b> ({med_t1} T1)</span>
        <span class="stat stat-low">Low (likely bare metal): <b>{len(low)}</b> ({low_t1} T1)</span>
    </div>
    <div class="legend">
        <span><span class="swatch swatch-high"></span> High — ready to pilot on VM</span>
        <span><span class="swatch swatch-med"></span> Medium — needs investigation</span>
        <span><span class="swatch swatch-low"></span> Low — likely needs bare metal</span>
        <span><span class="swatch swatch-perf"></span> Performance — excluded</span>
    </div>
    <div class="nav-bar">
        <a href="#high" class="nav-link" style="border-color: #27AE60;">High ({len(high)})</a>
        <a href="#medium" class="nav-link" style="border-color: #F39C12;">Medium ({len(med)})</a>
        <a href="#low" class="nav-link" style="border-color: #E74C3C;">Low ({len(low)})</a>
        <a href="#perf" class="nav-link" style="border-color: #555;">Performance ({len(perf)})</a>
        <a href="#context" class="nav-link" style="border-color: #4A90D9;">Context</a>
    </div>
</div>

<div class="content">

    <div class="section" id="high">
        <div class="section-header" style="border-left: 4px solid #27AE60;">
            <h2 style="color: #27AE60;">High Likelihood — Ready to Pilot</h2>
            <span class="section-stats">{len(high)} suites ({high_t1} tier 1) — already virtual on Linux/Windows, no GPU/video/heavy resource needs</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Reason</th>
            </tr></thead>
            <tbody>{make_rows(high)}</tbody>
        </table>
    </div>

    <div class="section" id="medium">
        <div class="section-header" style="border-left: 4px solid #F39C12;">
            <h2 style="color: #F39C12;">Medium Likelihood — Needs Investigation</h2>
            <span class="section-stats">{len(med)} suites ({med_t1} tier 1) — virtual on other platforms but has graphics/media/video dependencies to verify</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Reason</th>
            </tr></thead>
            <tbody>{make_rows(med)}</tbody>
        </table>
    </div>

    <div class="section" id="low">
        <div class="section-header" style="border-left: 4px solid #E74C3C;">
            <h2 style="color: #E74C3C;">Low Likelihood — Likely Needs Bare Metal</h2>
            <span class="section-stats">{len(low)} suites ({low_t1} tier 1) — heavy CPU/memory needs or requires hardware GL/video</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Reason</th>
            </tr></thead>
            <tbody>{make_rows(low)}</tbody>
        </table>
    </div>

    <div class="section" id="perf">
        <div class="section-header" style="border-left: 4px solid #555;">
            <h2 style="color: #888;">Performance Suites — Bare Metal Required</h2>
            <span class="section-stats">{len(perf)} suites — talos, browsertime, awsy (excluded from VM analysis)</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Reason</th>
            </tr></thead>
            <tbody>{make_rows(perf)}</tbody>
        </table>
    </div>

    <div class="context-box" id="context">
        <h2>Context and Methodology</h2>
        <p><b>Target setup:</b> Tart VMs on Mac Minis (16GB RAM, 2 VMs per host = ~8GB/VM, macOS licensing limit).</p>
        <p><b>Classification approach:</b></p>
        <ul>
            <li><b>High:</b> Suite runs as <code>virtualization: virtual</code> on Linux/Windows (default), uses default instance size, no GPU/video/heavy-CPU indicators in name or config.</li>
            <li><b>Medium:</b> Suite is virtual on other platforms but has graphics (reftest, WebGL, WebGPU, canvas, screenshots), media (video codecs, encrypted media), or loopback video dependencies that need verification on macOS VMs.</li>
            <li><b>Low:</b> Suite explicitly requires <code>highcpu</code> or <code>large</code> instance sizes, or needs both loopback video and hardware GL — likely exceeds 8GB VM capacity.</li>
            <li><b>Performance:</b> All talos, browsertime, and awsy suites — require bare metal for stable, reproducible performance numbers.</li>
        </ul>
        <p><b>Key finding:</b> macOS CI config has no virtualization branching — all tests go to physical Mac pools regardless. The <code>virtualization</code> field only affects Windows worker selection. This analysis uses the Linux/Windows virtual status as a proxy for "doesn't need bare metal."</p>
        <p><b>Architecture note:</b> Both Intel (Mac Mini) and Apple Silicon (M4 Mac Mini) hardware is in use. 115 tests only have coverage on Intel, 201 only on Apple Silicon. Neither architecture can be fully dropped without coverage loss.</p>
    </div>

</div>

</body>
</html>'''


if __name__ == "__main__":
    main()
