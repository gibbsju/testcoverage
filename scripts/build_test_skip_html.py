"""
Build an interactive HTML showing individual tests with skip status per OS.

Rows = individual tests (grouped by manifest/suite)
Columns = OS (Linux, Windows, macOS, Android)
Red dot = skipped on that OS
Green dot = runs on that OS (inferred from no skip condition targeting that OS)
Gray = not applicable (suite doesn't run on that OS)
"""

import re
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
FIREFOX = BASE / "firefox"

OS_LIST = ["linux", "win", "mac", "android"]
OS_DISPLAY = {"linux": "Linux", "win": "Windows", "mac": "macOS", "android": "Android"}


def extract_skip_conditions_toml(filepath):
    results = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return results

    current_test = None
    in_skip_if = False

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("[") and not stripped.startswith("[["):
            test_match = re.match(r'\["?([^"\]]+)"?\]', stripped)
            if test_match:
                current_test = test_match.group(1)
            in_skip_if = False

        if stripped.startswith("skip-if"):
            in_skip_if = True
            inline = re.match(r'skip-if\s*=\s*\[(.+)\]', stripped)
            if inline:
                for cond in re.findall(r'"([^"]+)"', inline.group(1)):
                    results.append((current_test or "DEFAULT", cond))
                in_skip_if = False
            continue

        if in_skip_if:
            if stripped == "]":
                in_skip_if = False
                continue
            for cond in re.findall(r'"([^"]+)"', stripped):
                results.append((current_test or "DEFAULT", cond))

    return results


def extract_os_from_condition(condition):
    targets = set()
    for m in re.finditer(r"os\s*==\s*['\"](\w+)['\"]", condition):
        targets.add(m.group(1))
    for m in re.finditer(r"os\s*!=\s*['\"](\w+)['\"]", condition):
        excluded = m.group(1)
        targets.update(set(OS_LIST) - {excluded})
    if condition.strip() == "true":
        targets.update(OS_LIST)
    # Build-only conditions (no OS) apply everywhere
    if not targets:
        build_patterns = [r"^debug$", r"^!debug$", r"^asan$", r"^tsan$", r"^verify", r"^ccov$"]
        for p in build_patterns:
            if re.match(p, condition.strip()):
                targets.update(OS_LIST)
                break
    return targets


def infer_suite_from_path(rel_path):
    """Guess the suite from the manifest filename."""
    fname = Path(rel_path).name.lower()
    if "xpcshell" in fname:
        return "xpcshell"
    elif "browser" in fname:
        return "mochitest-browser-chrome"
    elif "mochitest" in fname:
        return "mochitest-plain"
    elif "chrome" in fname:
        return "mochitest-chrome"
    elif "a11y" in fname:
        return "mochitest-a11y"
    elif "reftest" in fname:
        return "reftest"
    elif "crashtest" in fname:
        return "crashtest"
    else:
        return fname.replace(".toml", "")


def main():
    print("Scanning manifest files for skip-if annotations...")
    all_toml = list(FIREFOX.rglob("*.toml"))
    manifests = []
    for f in all_toml:
        if "node_modules" in str(f) or ".git" in str(f):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if "skip-if" in content:
                manifests.append(f)
        except Exception:
            continue

    print(f"  Found {len(manifests)} manifests with skip-if")

    # Parse all skips: {rel_path::test_name -> {os -> [conditions]}}
    test_skips = defaultdict(lambda: defaultdict(list))
    all_tests_in_manifest = defaultdict(set)  # rel_path -> set of test names

    for mf in manifests:
        rel = str(mf.relative_to(FIREFOX)).replace("\\", "/")
        skips = extract_skip_conditions_toml(mf)

        # Also extract all test names from the manifest
        try:
            content = mf.read_text(encoding="utf-8", errors="replace")
            for line in content.split("\n"):
                m = re.match(r'\["?([^"\]]+)"?\]', line.strip())
                if m and m.group(1) != "DEFAULT":
                    all_tests_in_manifest[rel].add(m.group(1))
        except Exception:
            pass

        for test_name, condition in skips:
            targets = extract_os_from_condition(condition)
            key = f"{rel}::{test_name}"
            for os_name in targets:
                test_skips[key][os_name].append(condition)
            if not targets:
                # Unresolved - store condition but don't mark any OS
                test_skips[key]["_unresolved"] = test_skips[key].get("_unresolved", [])
                test_skips[key]["_unresolved"].append(condition)

    # Build the data structure for HTML
    # Group by manifest (as a proxy for suite), then list tests
    manifest_groups = defaultdict(list)

    # First, add all tests that have skip conditions
    seen_keys = set()
    for key, os_map in test_skips.items():
        parts = key.split("::", 1)
        rel_path = parts[0]
        test_name = parts[1] if len(parts) > 1 else "DEFAULT"
        suite = infer_suite_from_path(rel_path)

        skip_info = {}
        for os_name in OS_LIST:
            if os_name in os_map:
                skip_info[os_name] = os_map[os_name]

        skipped_all = all(os_name in os_map for os_name in OS_LIST)
        unresolved = os_map.get("_unresolved", [])

        manifest_groups[suite].append({
            "test": test_name,
            "manifest": rel_path,
            "skips": skip_info,
            "skipped_all": skipped_all,
            "unresolved": unresolved,
        })
        seen_keys.add(key)

    # Sort groups by name, tests within by skip severity
    for suite in manifest_groups:
        manifest_groups[suite].sort(
            key=lambda t: (-sum(1 for os in OS_LIST if os in t["skips"]), t["test"])
        )

    # Count stats
    total_tests = sum(len(tests) for tests in manifest_groups.values())
    total_skipped_all = sum(
        1 for tests in manifest_groups.values()
        for t in tests if t["skipped_all"]
    )

    print(f"  Total tests with skip-if: {total_tests}")
    print(f"  Skipped on ALL platforms: {total_skipped_all}")
    print(f"  Suites: {len(manifest_groups)}")

    # Build HTML
    html = build_html(manifest_groups, total_tests, total_skipped_all)
    out = BASE / "docs" / "test_skip_matrix.html"
    out.write_text(html, encoding="utf-8")
    print(f"\nHTML saved to: {out}")


def build_html(manifest_groups, total_tests, total_skipped_all):
    suites_sorted = sorted(manifest_groups.keys())

    # Build suite nav
    suite_nav = []
    for suite in suites_sorted:
        count = len(manifest_groups[suite])
        skip_all = sum(1 for t in manifest_groups[suite] if t["skipped_all"])
        suite_nav.append(f'<a href="#suite-{suite}" class="suite-link">{suite} <span class="badge">{count}</span>'
                        + (f' <span class="badge-red">{skip_all} all-skip</span>' if skip_all else '')
                        + '</a>')

    # Build table rows per suite
    suite_sections = []
    for suite in suites_sorted:
        tests = manifest_groups[suite]
        skip_all_count = sum(1 for t in tests if t["skipped_all"])

        rows = []
        for t in tests:
            cells = []
            for os_name in OS_LIST:
                if os_name in t["skips"]:
                    conditions = t["skips"][os_name]
                    tooltip = "\\n".join(c.replace('"', '&quot;') for c in conditions)
                    cells.append(f'<td class="skip" title="{tooltip}"><span class="dot-red"></span></td>')
                else:
                    cells.append(f'<td class="runs"><span class="dot-green"></span></td>')

            # Skipped-all highlight
            row_class = ' class="row-danger"' if t["skipped_all"] else ""
            # Unresolved indicator
            unresolved_badge = ""
            if t["unresolved"]:
                tip = "\\n".join(t["unresolved"])
                unresolved_badge = f' <span class="badge-yellow" title="{tip}">?</span>'

            skip_count = sum(1 for os in OS_LIST if os in t["skips"])
            risk = "risk-high" if skip_count >= 4 else "risk-med" if skip_count >= 2 else "risk-low" if skip_count >= 1 else ""

            manifest_short = t["manifest"].split("/")[-2] + "/" + t["manifest"].split("/")[-1] if "/" in t["manifest"] else t["manifest"]

            rows.append(
                f'<tr{row_class}>'
                f'<td class="test-name">{t["test"]}{unresolved_badge}</td>'
                f'<td class="manifest-path">{manifest_short}</td>'
                + "".join(cells) +
                f'<td class="count-cell {risk}">{skip_count}/4</td>'
                f'</tr>'
            )

        section = f'''
        <div class="suite-section" id="suite-{suite}">
            <div class="suite-header">
                {suite}
                <span class="suite-count">{len(tests)} tests</span>
                {'<span class="suite-danger">' + str(skip_all_count) + ' skipped everywhere</span>' if skip_all_count else ''}
            </div>
            <table>
                <thead>
                    <tr>
                        <th class="th-test">Test</th>
                        <th class="th-manifest">Manifest</th>
                        <th class="th-os">Linux</th>
                        <th class="th-os">Windows</th>
                        <th class="th-os">macOS</th>
                        <th class="th-os">Android</th>
                        <th class="th-count">Skips</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        '''
        suite_sections.append(section)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Firefox CI: Test-Level Skip Matrix</title>
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
    z-index: 100;
    background: #0d1525;
    padding: 12px 20px;
    border-bottom: 2px solid #333;
}}
.top-bar h1 {{
    color: white;
    font-size: 20px;
    margin-bottom: 4px;
}}
.top-bar .subtitle {{
    color: #888;
    font-size: 12px;
    margin-bottom: 8px;
}}
.stats {{
    display: flex;
    gap: 20px;
    margin-bottom: 10px;
    font-size: 12px;
}}
.stat {{ color: #aaa; }}
.stat b {{ color: white; }}
.stat-danger b {{ color: #E74C3C; }}
.legend {{
    display: flex;
    gap: 18px;
    font-size: 12px;
    margin-bottom: 8px;
}}
.legend span {{ display: flex; align-items: center; gap: 5px; }}
.dot-legend {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
.dot-legend-red {{ background: #E74C3C; }}
.dot-legend-green {{ background: #27AE60; }}
.dot-legend-yellow {{ background: #F39C12; }}
.filter-bar {{
    display: flex;
    gap: 10px;
    align-items: center;
    margin-top: 6px;
}}
.filter-bar input {{
    background: #16213e;
    border: 1px solid #444;
    color: white;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    width: 250px;
    font-family: inherit;
}}
.filter-bar label {{
    color: #aaa;
    font-size: 12px;
    cursor: pointer;
}}
.filter-bar input[type="checkbox"] {{
    accent-color: #E74C3C;
}}
.sidebar {{
    position: fixed;
    left: 0;
    top: 140px;
    bottom: 0;
    width: 240px;
    background: #0d1525;
    border-right: 1px solid #333;
    overflow-y: auto;
    padding: 10px;
    z-index: 50;
}}
.sidebar h3 {{
    color: #888;
    font-size: 11px;
    text-transform: uppercase;
    margin-bottom: 8px;
}}
.suite-link {{
    display: block;
    color: #4A90D9;
    text-decoration: none;
    font-size: 12px;
    padding: 3px 6px;
    border-radius: 3px;
    margin-bottom: 2px;
}}
.suite-link:hover {{ background: #1e2a4a; }}
.badge {{
    background: #2a3a5a;
    color: #aaa;
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 8px;
}}
.badge-red {{
    background: #5a1a1a;
    color: #E74C3C;
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 8px;
}}
.badge-yellow {{
    background: #5a4a1a;
    color: #F39C12;
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 8px;
    cursor: help;
}}
.content {{
    margin-left: 250px;
    padding: 16px 20px;
}}
.suite-section {{
    margin-bottom: 24px;
}}
.suite-header {{
    font-size: 16px;
    font-weight: bold;
    color: white;
    padding: 10px 0 6px 0;
    border-bottom: 2px solid #4A90D9;
    margin-bottom: 4px;
}}
.suite-count {{
    color: #888;
    font-size: 12px;
    font-weight: normal;
    margin-left: 10px;
}}
.suite-danger {{
    color: #E74C3C;
    font-size: 12px;
    font-weight: normal;
    margin-left: 10px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
}}
thead th {{
    position: sticky;
    top: 135px;
    background: #0d1525;
    z-index: 10;
    padding: 6px 8px;
    font-size: 11px;
    color: #aaa;
    text-align: center;
    border-bottom: 1px solid #444;
}}
.th-test {{ text-align: left; min-width: 300px; }}
.th-manifest {{ text-align: left; min-width: 200px; color: #666; }}
.th-os {{ min-width: 80px; }}
.th-count {{ min-width: 50px; }}
td {{
    padding: 4px 8px;
    border-bottom: 1px solid #1e2a4a;
    text-align: center;
    font-size: 12px;
}}
.test-name {{
    text-align: left;
    color: #ddd;
    max-width: 400px;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.manifest-path {{
    text-align: left;
    color: #555;
    font-size: 11px;
    max-width: 250px;
    overflow: hidden;
    text-overflow: ellipsis;
}}
tr:nth-child(even) {{ background: #1a1a2e; }}
tr:nth-child(odd) {{ background: #16213e; }}
tr:hover {{ background: #2a3a5a !important; }}
tr.row-danger {{ background: #2a1515 !important; }}
tr.row-danger:hover {{ background: #3a2020 !important; }}
tr.hidden {{ display: none; }}
.dot-red {{
    width: 16px; height: 16px; border-radius: 50%;
    display: inline-block; background: #E74C3C;
}}
.dot-green {{
    width: 16px; height: 16px; border-radius: 50%;
    display: inline-block; background: #27AE60; opacity: 0.5;
}}
.skip {{ cursor: help; }}
.count-cell {{ color: #aaa; font-size: 11px; }}
.risk-high {{ color: #E74C3C; font-weight: bold; }}
.risk-med {{ color: #F39C12; }}
.risk-low {{ color: #27AE60; }}
</style>
</head>
<body>

<div class="top-bar">
    <h1>Firefox CI: Test-Level Skip Matrix</h1>
    <p class="subtitle">Red = skipped on that OS | Green = runs | Hover red dots for skip condition | Grouped by suite</p>
    <div class="stats">
        <span class="stat">Tests with skips: <b>{total_tests}</b></span>
        <span class="stat stat-danger">Skipped on ALL platforms: <b>{total_skipped_all}</b></span>
        <span class="stat">Suites: <b>{len(manifest_groups)}</b></span>
    </div>
    <div class="legend">
        <span><span class="dot-legend dot-legend-red"></span> Skipped</span>
        <span><span class="dot-legend dot-legend-green"></span> Runs</span>
        <span><span class="dot-legend dot-legend-yellow"></span> Unresolved condition</span>
    </div>
    <div class="filter-bar">
        <input type="text" id="filter" placeholder="Filter tests..." oninput="applyFilters()">
        <label><input type="checkbox" id="showDangerOnly" onchange="applyFilters()"> Show only skipped-everywhere</label>
    </div>
</div>

<div class="sidebar">
    <h3>Suites</h3>
    {"".join(suite_nav)}
</div>

<div class="content">
    {"".join(suite_sections)}
</div>

<script>
function applyFilters() {{
    const query = document.getElementById('filter').value.toLowerCase();
    const dangerOnly = document.getElementById('showDangerOnly').checked;
    document.querySelectorAll('tbody tr').forEach(row => {{
        const text = row.textContent.toLowerCase();
        const isDanger = row.classList.contains('row-danger');
        const matchQuery = !query || text.includes(query);
        const matchDanger = !dangerOnly || isDanger;
        row.classList.toggle('hidden', !(matchQuery && matchDanger));
    }});
}}
</script>

</body>
</html>'''


if __name__ == "__main__":
    main()
