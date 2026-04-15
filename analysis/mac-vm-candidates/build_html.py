"""
Build an HTML page showing macOS functional test suites categorized by
VM migration feasibility for Tart on Mac Minis.

Categories are validated against actual try push results on
VirtualMac2,1 (8GB RAM, 4 cores — matching target spec).
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

# --- Try push results (VirtualMac2,1 — 8GB RAM, 4 cores) ---
# These override the config-based classification with real-world data.

TRY_PUSH = {
    # VERIFIED — passed on VM
    "cppunittest":                  ("verified",  "Passed opt + debug on VM"),
    "marionette-integration":       ("verified",  "Passed on VM"),
    "web-platform-tests-crashtest": ("verified",  "Passed on VM"),
    "mochitest-plain-gpu":          ("verified",  "Passed on VM (GPU works in Tart)"),
    "mochitest-webgl1-ext":         ("verified",  "Passed on VM (WebGL extensions work)"),
    "mochitest-webgl2-ext":         ("verified",  "Passed 3/4 chunks on VM (ext-1 fails)"),
    "telemetry-tests-client":       ("verified",  "Passed on VM"),
    "web-platform-tests-eme":       ("verified",  "Passed on VM (encrypted media works)"),
    "web-platform-tests-print-reftest": ("verified", "Passed on VM (print rendering works)"),

    # FIXABLE — partially working, known path to fix
    "jittest":                      ("fixable",   "debug passes, opt fails due to x86_64 libnss3.dylib packaging bug (not VM-specific)"),
    "web-platform-tests":           ("fixable",   "~7/13 chunks pass; some COEP/touch failures + timeouts need annotation"),
    "web-platform-tests-wdspec":    ("fixable",   "7/9 variants pass; wdspec-3/-5 fail on window focus (VMs don't focus background windows)"),
    "firefox-ui-functional":        ("fixable",   "SafeBrowsing file list mismatch — test expectation update, not a VM issue"),
    "mochitest-plain":              ("fixable",   "Timeout cascade — tests hit 300s limit on slower VM; fixable with timeout tuning/chunk sizing"),
    "mochitest-chrome":             ("fixable",   "Same timeout cascade as mochitest-plain"),
    "mochitest-devtools-chrome":    ("fixable",   "Same timeout cascade"),
    "mochitest-a11y":               ("fixable",   "Same timeout cascade"),
    "marionette-unittest":          ("fixable",   "Window focus test fails — skip focus-dependent variants on VM"),

    # BLOCKED — real VM blockers, need investigation
    "crashtest":                    ("blocked",   "Application hang — Firefox starts, Marionette connects, then nothing for 1000s (macOS VM-specific)"),
    "mochitest-browser-chrome":     ("blocked",   "Application hang — browser-chrome harness never starts executing tests"),
    "mochitest-browser-a11y":       ("blocked",   "Same application hang"),
    "mochitest-browser-translations": ("blocked", "Same application hang"),
    "mochitest-browser-media":      ("blocked",   "Same application hang (browser-chrome pattern)"),
    "mochitest-remote":             ("blocked",   "Unclassified failure — needs investigation"),
    "reftest":                      ("blocked",   "Application hang — same as crashtest (reftest harness hang on macOS VMs)"),
    "jsreftest":                    ("blocked",   "Same reftest harness hang"),
    "mochitest-webgl1-core":        ("blocked",   "WebGL core tests fail (but extension tests pass)"),
    "mochitest-webgl2-core":        ("blocked",   "Same — core fails, extensions pass"),
    "mochitest-chrome-gpu":         ("blocked",   "Timeout cascade"),
    "web-platform-tests-canvas":    ("blocked",   "Canvas rendering failures"),
    "web-platform-tests-reftest":   ("blocked",   "Rendering failures"),
    "web-platform-tests-webcodecs": ("blocked",   "Media codec failures"),

    # CONFIRMED LOW — try push validates bare metal classification
    "gtest":                        ("confirmed-low", "SIGSEGV crash during WebRTC/SRTP tests after 13,199 tests"),
    "xpcshell":                     ("confirmed-low", "16 crash dumps; crash-recovery tests + enterprise CA config differ in VM"),
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
    """Classify using try push results first, then fall back to config analysis."""

    # Try push override
    if name in TRY_PUSH:
        status, reason = TRY_PUSH[name]
        return status, reason

    # Performance suites
    if any(name.startswith(pf) for pf in PERF_PREFIXES):
        return "perf", "Performance suite — bare metal required"

    p = props.get(name, {})
    virt = p.get("virtualization", "virtual")
    if virt == "hardware":
        return "perf", "Explicit hardware virtualization"

    inst = p.get("instance_size", "default")
    video = p.get("loopback_video", False)
    sw_gl = p.get("allow_sw_gl", True)

    is_heavy = False
    if isinstance(inst, str) and ("large" in inst.lower() or "high" in inst.lower()):
        is_heavy = True
    if isinstance(inst, dict):
        for v in str(inst).lower().split():
            if "highcpu" in v or "large" in v:
                is_heavy = True

    if is_heavy:
        return "not-tested", f"Heavy resources (instance-size: {inst}) — not in try push"
    if video and sw_gl == False:
        return "not-tested", "Requires loopback video + hardware GL — not in try push"

    gpu_keywords = ["gpu", "webgl", "webgpu"]
    graphics_keywords = ["reftest", "canvas", "screenshot"]
    media_keywords = ["media", "webcodecs", "eme"]

    if any(k in name.lower() for k in gpu_keywords + graphics_keywords + media_keywords):
        return "not-tested", "Graphics/media suite — not in try push"

    return "not-tested", "Not in try push — config suggests virtual-capable"


def main():
    print("Building macOS VM candidates HTML (with try push validation)...")

    tier_data = json.loads((ANALYSIS / "tier_matrix.json").read_text(encoding="utf-8"))
    skip_data = json.loads((ANALYSIS / "tier_skip_crossref.json").read_text(encoding="utf-8"))
    mac_plats = tier_data["platforms_by_os"].get("macOS", [])
    mac_t1_plats = [p for p in mac_plats if p in TIER_1_SET]
    matrix = tier_data["matrix"]

    mac_platforms = get_mac_platforms()
    suite_props = get_suite_properties()

    mac_suites = set()
    for plat_name, plat_def in mac_platforms.items():
        test_set_names = plat_def.get("test-sets", [])
        mac_suites.update(expand_test_sets(test_set_names))

    classified = []
    for suite in sorted(mac_suites):
        likelihood, reason = classify_suite(suite, suite_props)
        is_t1 = any(matrix.get(suite, {}).get(p) == 1 for p in mac_t1_plats)
        skip_info = skip_data.get("suites", {}).get(suite, {})
        skipped = skip_info.get("total_skipped", 0)
        skipped_all = skip_info.get("skipped_all_platforms", 0)

        runs_on = []
        for plat_name, plat_def in mac_platforms.items():
            plat_suites = expand_test_sets(plat_def.get("test-sets", []))
            if suite in plat_suites:
                hw = None
                for base, info in WORKER_MAP.items():
                    if plat_name.startswith(base):
                        hw = info
                        break
                runs_on.append({"platform": plat_name, "arch": hw["arch"] if hw else "?"})

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

    html = build_html(classified)
    out = BASE / "docs" / "mac_vm_candidates.html"
    out.write_text(html, encoding="utf-8")
    print(f"  HTML saved to: {out}")

    for cat in ["verified", "fixable", "blocked", "confirmed-low", "not-tested", "perf"]:
        items = [c for c in classified if c["likelihood"] == cat]
        if items:
            print(f"  {cat}: {len(items)}")


def build_html(classified):
    verified = [c for c in classified if c["likelihood"] == "verified"]
    fixable = [c for c in classified if c["likelihood"] == "fixable"]
    blocked = [c for c in classified if c["likelihood"] == "blocked"]
    confirmed_low = [c for c in classified if c["likelihood"] == "confirmed-low"]
    not_tested = [c for c in classified if c["likelihood"] == "not-tested"]
    perf = [c for c in classified if c["likelihood"] == "perf"]

    total_functional = len(verified) + len(fixable) + len(blocked) + len(confirmed_low) + len(not_tested)
    verified_t1 = sum(1 for c in verified if c["tier"] == 1)
    fixable_t1 = sum(1 for c in fixable if c["tier"] == 1)
    blocked_t1 = sum(1 for c in blocked if c["tier"] == 1)

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
<title>macOS VM Migration Candidates (Try Push Validated)</title>
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
.stat-verified b {{ color: #27AE60; }}
.stat-fixable b {{ color: #3498DB; }}
.stat-blocked b {{ color: #E74C3C; }}
.legend {{
    display: flex;
    gap: 14px;
    font-size: 12px;
    margin-bottom: 8px;
    flex-wrap: wrap;
}}
.legend span {{ display: flex; align-items: center; gap: 5px; }}
.swatch {{ width: 14px; height: 14px; display: inline-block; border-radius: 2px; }}
.swatch-verified {{ background: #27AE60; }}
.swatch-fixable {{ background: #3498DB; }}
.swatch-blocked {{ background: #E74C3C; }}
.swatch-low {{ background: #E74C3C; opacity: 0.5; }}
.swatch-nottested {{ background: #888; }}
.swatch-perf {{ background: #555; }}
.nav-bar {{
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
    flex-wrap: wrap;
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
    <p class="subtitle">Validated against try push on VirtualMac2,1 (8GB RAM, 4 cores) — matches Tart on Mac Mini target spec</p>
    <div class="stats">
        <span class="stat">Functional suites: <b>{total_functional}</b></span>
        <span class="stat">Performance (bare metal): <b>{len(perf)}</b></span>
        <span class="stat stat-verified">Verified on VM: <b>{len(verified)}</b> ({verified_t1} T1)</span>
        <span class="stat stat-fixable">Fixable: <b>{len(fixable)}</b> ({fixable_t1} T1)</span>
        <span class="stat stat-blocked">Blocked: <b>{len(blocked)}</b> ({blocked_t1} T1)</span>
        <span class="stat">Confirmed bare metal: <b>{len(confirmed_low)}</b></span>
        <span class="stat">Not tested: <b>{len(not_tested)}</b></span>
    </div>
    <div class="legend">
        <span><span class="swatch swatch-verified"></span> Verified — passed on VM</span>
        <span><span class="swatch swatch-fixable"></span> Fixable — known path to resolve</span>
        <span><span class="swatch swatch-blocked"></span> Blocked — VM-specific issue</span>
        <span><span class="swatch swatch-low"></span> Confirmed bare metal</span>
        <span><span class="swatch swatch-nottested"></span> Not tested yet</span>
        <span><span class="swatch swatch-perf"></span> Performance — excluded</span>
    </div>
    <div class="nav-bar">
        <a href="#verified" class="nav-link" style="border-color: #27AE60;">Verified ({len(verified)})</a>
        <a href="#fixable" class="nav-link" style="border-color: #3498DB;">Fixable ({len(fixable)})</a>
        <a href="#blocked" class="nav-link" style="border-color: #E74C3C;">Blocked ({len(blocked)})</a>
        <a href="#confirmed-low" class="nav-link" style="border-color: #8B0000;">Confirmed Bare Metal ({len(confirmed_low)})</a>
        <a href="#not-tested" class="nav-link" style="border-color: #888;">Not Tested ({len(not_tested)})</a>
        <a href="#perf" class="nav-link" style="border-color: #555;">Performance ({len(perf)})</a>
        <a href="#context" class="nav-link" style="border-color: #4A90D9;">Context</a>
    </div>
</div>

<div class="content">

    <div class="section" id="verified">
        <div class="section-header" style="border-left: 4px solid #27AE60;">
            <h2 style="color: #27AE60;">Verified — Passed on VM</h2>
            <span class="section-stats">{len(verified)} suites ({verified_t1} tier 1) — confirmed working on VirtualMac2,1</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Try Push Result</th>
            </tr></thead>
            <tbody>{make_rows(verified)}</tbody>
        </table>
    </div>

    <div class="section" id="fixable">
        <div class="section-header" style="border-left: 4px solid #3498DB;">
            <h2 style="color: #3498DB;">Fixable — Known Path to Resolve</h2>
            <span class="section-stats">{len(fixable)} suites ({fixable_t1} tier 1) — partially working, timeout tuning / test annotation / packaging fixes needed</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Issue + Fix</th>
            </tr></thead>
            <tbody>{make_rows(fixable)}</tbody>
        </table>
    </div>

    <div class="section" id="blocked">
        <div class="section-header" style="border-left: 4px solid #E74C3C;">
            <h2 style="color: #E74C3C;">Blocked — VM-Specific Issues</h2>
            <span class="section-stats">{len(blocked)} suites ({blocked_t1} tier 1) — application hangs, rendering failures, or unclassified issues on macOS VMs</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Root Cause</th>
            </tr></thead>
            <tbody>{make_rows(blocked)}</tbody>
        </table>
    </div>

    <div class="section" id="confirmed-low">
        <div class="section-header" style="border-left: 4px solid #8B0000;">
            <h2 style="color: #CD5C5C;">Confirmed Bare Metal</h2>
            <span class="section-stats">{len(confirmed_low)} suites — try push confirms these need bare metal</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Root Cause</th>
            </tr></thead>
            <tbody>{make_rows(confirmed_low)}</tbody>
        </table>
    </div>

    <div class="section" id="not-tested">
        <div class="section-header" style="border-left: 4px solid #888;">
            <h2 style="color: #aaa;">Not Tested Yet</h2>
            <span class="section-stats">{len(not_tested)} suites — not included in try push, classification based on config analysis only</span>
        </div>
        <table>
            <thead><tr>
                <th>Suite</th><th class="center">Tier</th><th class="center">Arch</th>
                <th class="center">Skips</th><th class="center">All-Plat</th><th>Config Assessment</th>
            </tr></thead>
            <tbody>{make_rows(not_tested)}</tbody>
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
        <p><b>Try push environment:</b> VirtualMac2,1, 8GB RAM, 4 cores — matches target Tart spec (16GB Mac Mini / 2 VMs).</p>
        <p><b>Classification (validated):</b></p>
        <ul>
            <li><b>Verified:</b> Suite passed on the try push VM. Ready for production VM rollout.</li>
            <li><b>Fixable:</b> Partially working. Known fixes: timeout tuning for VM slowness, skip window-focus tests, update test expectations, fix packaging bugs.</li>
            <li><b>Blocked:</b> Real VM-specific issues. The biggest blocker is the <b>browser-chrome / reftest harness hang</b> — Firefox starts, Marionette connects, then nothing for 1000s. This is macOS VM-specific (works on Linux VMs) and affects the largest cluster of suites. Resolving this single issue would unblock crashtest, mochitest-browser-chrome, browser-a11y, browser-translations, browser-media, reftest, and jsreftest.</li>
            <li><b>Confirmed bare metal:</b> Try push confirms these crash or fail fundamentally on VMs (gtest SIGSEGV, xpcshell crash recovery).</li>
            <li><b>Not tested:</b> Config analysis suggests these may be VM-capable but they weren't in the try push. Needs future validation.</li>
        </ul>
        <p><b>Key finding from try push:</b> Config-based analysis (virtualization: virtual on Linux/Windows) correctly predicts resource/GPU compatibility but cannot detect macOS VM-specific runtime behaviors like the harness hang and window focus issues. Real try push validation is essential.</p>
        <p><b>Positive surprise:</b> Tart VMs have working GPU — mochitest-plain-gpu, WebGL extension tests, encrypted media, and print rendering all passed. Several suites originally classified as "Medium" were promoted to "Verified."</p>
    </div>

</div>

</body>
</html>'''


if __name__ == "__main__":
    main()
