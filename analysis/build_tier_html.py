"""
Build an interactive HTML page showing the suite x platform tier matrix.

Layout: one section per OS family (Linux, Windows, macOS, Android),
each with suites as rows and that OS's platforms as columns.
Vertical scrolling only — no left/right scroll.
"""

import re
import yaml
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
FIREFOX = BASE / "firefox"
TC = FIREFOX / "taskcluster"

TIER_1_PLATFORMS = [
    "linux64/opt", "linux64/debug", "linux64-shippable/opt",
    "linux64-devedition/opt", "linux64-asan/opt",
    "linux64-qr/opt", "linux64-qr/debug", "linux64-shippable-qr/opt",
    "linux2204-64-wayland/debug", "linux2204-64-wayland/opt",
    "linux2204-64-wayland-shippable/opt",
    "linux2404-64/opt", "linux2404-64/debug", "linux2404-64-shippable/opt",
    "linux2404-64-devedition/opt", "linux2404-64-asan/opt", "linux2404-64-tsan/opt",
    "windows11-32-24h2/debug", "windows11-32-24h2/opt",
    "windows11-32-24h2-shippable/opt",
    "windows11-64-24h2-hw-ref/opt", "windows11-64-24h2-hw-ref-shippable/opt",
    "windows11-64-24h2/opt", "windows11-64-24h2/debug",
    "windows11-64-24h2-shippable/opt", "windows11-64-24h2-devedition/opt",
    "windows11-64-24h2-asan/opt",
    "macosx1015-64/opt", "macosx1015-64/debug", "macosx1015-64-shippable/opt",
    "macosx1015-64-devedition/opt", "macosx1015-64-devedition-qr/opt",
    "macosx1015-64-qr/opt", "macosx1015-64-shippable-qr/opt",
    "macosx1015-64-qr/debug",
    "macosx1470-64/opt", "macosx1470-64/debug", "macosx1470-64-shippable/opt",
    "macosx1470-64-devedition/opt",
    "macosx1400-64-shippable-qr/opt", "macosx1400-64-qr/debug",
    "macosx1500-64-shippable/opt", "macosx1500-64/debug",
    "android-em-14-x86_64-shippable/opt", "android-em-14-x86_64/opt",
    "android-em-14-x86_64-shippable-lite/opt", "android-em-14-x86_64-lite/opt",
    "android-em-14-x86_64/debug", "android-em-14-x86_64/debug-isolated-process",
    "android-em-14-x86-shippable/opt", "android-em-14-x86/opt",
]
TIER_1_SET = set(TIER_1_PLATFORMS)

OS_COLORS = {
    "Linux": "#F39C12",
    "Windows": "#3498DB",
    "macOS": "#9B59B6",
    "Android": "#27AE60",
}


def platform_os(platform):
    if platform.startswith("linux"):
        return "Linux"
    elif platform.startswith("windows"):
        return "Windows"
    elif platform.startswith("macosx"):
        return "macOS"
    elif platform.startswith("android"):
        return "Android"
    return "Other"


def platform_short(platform):
    """Make platform name readable by stripping the OS prefix."""
    p = platform
    for prefix in [
        "linux2404-64-", "linux2204-64-", "linux64-",
        "windows11-64-24h2-", "windows11-32-24h2-", "windows11-aarch64-24h2-",
        "macosx1500-64-", "macosx1470-64-", "macosx1400-64-",
        "macosx1015-64-",
        "android-em-14-x86_64-", "android-em-14-x86-",
        "android-hw-a55-14-arm7-", "android-hw-s24-14-arm8-",
    ]:
        if p.startswith(prefix):
            remainder = p[len(prefix):]
            return remainder if remainder else "base"
    # Fallback: just return after last dash-group or the build type
    return p


def parse_kind_tiers():
    suite_tiers = {}
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
        for suite_name, suite_def in data.items():
            if suite_name == "task-defaults" or not isinstance(suite_def, dict):
                continue
            if "tier" in suite_def:
                suite_tiers[suite_name] = suite_def["tier"]
    return suite_tiers


def parse_variant_overrides():
    variants_file = TC / "test_configs" / "variants.yml"
    data = yaml.safe_load(variants_file.read_text(encoding="utf-8"))
    overrides = {}
    for variant_name, variant_def in data.items():
        if not isinstance(variant_def, dict):
            continue
        replace = variant_def.get("replace", {})
        if isinstance(replace, dict) and "tier" in replace:
            overrides[variant_name] = {
                "tier": replace["tier"],
                "when": variant_def.get("when", {}).get("$eval", "always"),
                "suffix": variant_def.get("suffix", variant_name),
            }
    return overrides


def resolve_tier(suite, platform, suite_tiers):
    if suite in suite_tiers:
        tier_def = suite_tiers[suite]
        if isinstance(tier_def, int):
            return tier_def
        if isinstance(tier_def, dict) and "by-test-platform" in tier_def:
            keyed = tier_def["by-test-platform"]
            for pattern, value in keyed.items():
                if pattern == "default":
                    continue
                if re.match(pattern, platform):
                    if isinstance(value, int):
                        return value
                    break
            default_val = keyed.get("default", "default")
            if isinstance(default_val, int):
                return default_val
    return 1 if platform in TIER_1_SET else 2


def get_test_platforms():
    tp_file = TC / "test_configs" / "test-platforms.yml"
    data = yaml.safe_load(tp_file.read_text(encoding="utf-8"))
    return sorted(data.keys()) if data else []


def get_all_suites(suite_tiers):
    ts_file = TC / "test_configs" / "test-sets.yml"
    data = yaml.safe_load(ts_file.read_text(encoding="utf-8"))
    all_suites = set()
    if data:
        for test_set, suites in data.items():
            if isinstance(suites, list):
                all_suites.update(suites)
    all_suites.update(suite_tiers.keys())
    return sorted(all_suites)


def build_os_section(os_name, os_plats, suites, matrix, suite_tiers):
    """Build one OS section with its platforms as columns."""
    color = OS_COLORS.get(os_name, "#ccc")
    t1_count = sum(1 for p in os_plats if p in TIER_1_SET)
    t2_count = len(os_plats) - t1_count

    # Column headers
    headers = f'<th class="th-suite">Suite</th><th class="th-tier">T1</th><th class="th-tier">T2</th>'
    for p in os_plats:
        short = platform_short(p)
        is_t1 = p in TIER_1_SET
        cls = "th-plat t1-plat" if is_t1 else "th-plat"
        headers += f'<th class="{cls}" title="{p}">{short}</th>'

    # Rows
    rows = []
    for suite in suites:
        tiers = [matrix[suite].get(p, "-") for p in os_plats]
        t1_n = sum(1 for t in tiers if t == 1)
        t2_n = sum(1 for t in tiers if t == 2)
        t3_n = sum(1 for t in tiers if t == 3)

        # Determine row class for filtering
        if t1_n > 0 and t2_n == 0 and t3_n == 0:
            row_cls = "row-all-t1"
        elif t1_n == 0 and t3_n == 0:
            row_cls = "row-all-t2"
        elif t1_n == 0 and t2_n == 0:
            row_cls = "row-all-t3"
        else:
            row_cls = "row-mixed"

        cells = f'<td class="suite-name">{suite}</td>'
        cells += f'<td class="count-t1">{t1_n}</td>'
        cells += f'<td class="count-t2">{t2_n}</td>'

        for p in os_plats:
            tier = matrix[suite].get(p, "-")
            cells += f'<td class="tier tier-{tier}">{tier}</td>'

        rows.append(f'<tr class="suite-row {row_cls}" data-suite="{suite}">{cells}</tr>')

    section_id = os_name.lower().replace(" ", "")

    return f'''
    <div class="os-section" id="os-{section_id}">
        <div class="os-header" style="border-left: 4px solid {color};">
            <h2 style="color: {color};">{os_name}</h2>
            <span class="os-stats">{len(os_plats)} platforms ({t1_count} tier 1, {t2_count} tier 2)</span>
        </div>
        <table>
            <thead><tr>{headers}</tr></thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
    </div>
    '''


def build_html(suites, platforms, matrix, variant_overrides, suite_tiers):
    os_order = ["Linux", "Windows", "macOS", "Android"]
    os_groups = defaultdict(list)
    for p in platforms:
        os_groups[platform_os(p)].append(p)

    total_suites = len(suites)

    # Build OS sections
    os_sections = []
    for os_name in os_order:
        os_plats = os_groups.get(os_name, [])
        if os_plats:
            os_sections.append(build_os_section(os_name, os_plats, suites, matrix, suite_tiers))

    # Nav links
    nav_links = ""
    for os_name in os_order:
        color = OS_COLORS.get(os_name, "#ccc")
        section_id = os_name.lower().replace(" ", "")
        count = len(os_groups.get(os_name, []))
        t1 = sum(1 for p in os_groups.get(os_name, []) if p in TIER_1_SET)
        nav_links += f'<a href="#os-{section_id}" class="nav-link" style="border-color: {color};">{os_name} <span class="nav-count">{count} plats, {t1} T1</span></a>'

    # Variant overrides
    variant_rows = ""
    for name, info in sorted(variant_overrides.items()):
        when = info["when"] if isinstance(info["when"], str) else str(info["when"])
        variant_rows += f'<tr><td class="var-name">{name}</td><td class="tier tier-{info["tier"]}">Tier {info["tier"]}</td><td class="var-when">{when}</td></tr>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Firefox CI: Suite x Platform Tier Matrix</title>
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
.top-bar .subtitle {{ color: #888; font-size: 12px; margin-bottom: 8px; }}
.stats {{
    display: flex;
    gap: 20px;
    margin-bottom: 8px;
    font-size: 12px;
}}
.stat {{ color: #aaa; }}
.stat b {{ color: white; }}
.legend {{
    display: flex;
    gap: 18px;
    font-size: 12px;
    margin-bottom: 8px;
}}
.legend span {{ display: flex; align-items: center; gap: 5px; }}
.swatch {{ width: 14px; height: 14px; display: inline-block; border-radius: 2px; }}
.swatch-t1 {{ background: #27AE60; }}
.swatch-t2 {{ background: #F39C12; }}
.swatch-t3 {{ background: #E74C3C; }}
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
    border-left: 3px solid;
    background: #16213e;
    font-size: 12px;
}}
.nav-link:hover {{ background: #2a3a5a; }}
.nav-count {{ color: #888; font-size: 11px; }}
.filter-bar {{
    display: flex;
    gap: 10px;
    align-items: center;
}}
.filter-bar input[type="text"] {{
    background: #16213e;
    border: 1px solid #444;
    color: white;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    width: 250px;
    font-family: inherit;
}}
.filter-bar label {{ color: #aaa; font-size: 12px; cursor: pointer; }}
.filter-bar input[type="checkbox"] {{ accent-color: #27AE60; }}
.filter-bar select {{
    background: #16213e;
    border: 1px solid #444;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-family: inherit;
}}
.content {{
    padding: 16px 20px;
    max-width: 1400px;
}}
.os-section {{
    margin-bottom: 30px;
}}
.os-header {{
    padding: 8px 12px;
    margin-bottom: 0;
    background: #0d1525;
    border-radius: 4px 4px 0 0;
}}
.os-header h2 {{ font-size: 18px; display: inline; margin-right: 12px; }}
.os-stats {{ color: #888; font-size: 12px; }}
.sticky-banner {{
    display: none;
    position: fixed;
    z-index: 100;
    left: 0;
    right: 0;
    background: #0d1525;
    border-bottom: none;
    padding: 6px 20px;
}}
.sticky-banner h3 {{ font-size: 14px; display: inline; margin-right: 10px; }}
.sticky-banner .os-stats {{ display: inline; }}
.sticky-cols {{
    display: none;
    position: fixed;
    z-index: 99;
    left: 0;
    right: 0;
    background: #0d1525;
    padding: 0 20px;
    border-bottom: 1px solid #444;
    overflow: hidden;
    margin-top: 0;
}}
.sticky-cols table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
.sticky-cols th {{
    padding: 4px 3px;
    font-size: 10px;
    color: #aaa;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}}
thead th {{
    background: #0d1525;
    padding: 4px 3px;
    font-size: 10px;
    color: #aaa;
    text-align: center;
    border-bottom: 1px solid #444;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.th-suite {{ text-align: left; width: 280px; min-width: 280px; max-width: 280px; }}
.th-tier {{ width: 30px; min-width: 30px; max-width: 30px; }}
.th-plat {{ font-size: 9px; }}
.t1-plat {{ color: #27AE60; font-weight: bold; }}
td {{
    padding: 3px 3px;
    text-align: center;
    font-size: 11px;
    border-bottom: 1px solid #1e2a4a;
    overflow: hidden;
}}
.suite-name {{
    text-align: left;
    color: #ddd;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 280px;
    min-width: 280px;
    max-width: 280px;
}}
.count-t1 {{ color: #27AE60; font-size: 10px; }}
.count-t2 {{ color: #F39C12; font-size: 10px; }}
tr:nth-child(even) {{ background: #1a1a2e; }}
tr:nth-child(odd) {{ background: #16213e; }}
tr:hover {{ background: #2a3a5a !important; }}
tr.hidden {{ display: none; }}
.tier {{ font-weight: bold; font-size: 11px; }}
.tier-1 {{ color: #27AE60; }}
.tier-2 {{ color: #F39C12; }}
.tier-3 {{ color: #E74C3C; }}
.row-all-t2 .suite-name {{ color: #999; }}
.row-all-t3 .suite-name {{ color: #777; }}
.variant-section {{
    margin-top: 30px;
    padding: 16px;
    background: #0d1525;
    border-radius: 6px;
    border: 1px solid #333;
}}
.variant-section h2 {{ color: white; font-size: 16px; margin-bottom: 10px; }}
.variant-table {{ width: 100%; }}
.variant-table th {{ text-align: left; color: #888; padding: 4px 8px; border-bottom: 1px solid #444; font-size: 12px; }}
.variant-table td {{ padding: 4px 8px; border-bottom: 1px solid #1e2a4a; font-size: 12px; }}
.var-name {{ color: #ddd; font-weight: bold; }}
.var-when {{ color: #888; font-size: 11px; max-width: 700px; word-break: break-all; }}
</style>
</head>
<body>

<div class="top-bar">
    <h1>Firefox CI: Suite x Platform Tier Matrix</h1>
    <p class="subtitle">Tier 1 = must pass before code lands | Tier 2 = secondary | Tier 3 = experimental | Green headers = Tier 1 platforms</p>
    <div class="stats">
        <span class="stat">Suites: <b>{total_suites}</b></span>
        <span class="stat">Platforms: <b>{len(platforms)}</b></span>
        <span class="stat">Tier 1 platforms: <b>{len(TIER_1_PLATFORMS)}</b></span>
    </div>
    <div class="legend">
        <span><span class="swatch swatch-t1"></span> Tier 1 (must pass)</span>
        <span><span class="swatch swatch-t2"></span> Tier 2 (secondary)</span>
        <span><span class="swatch swatch-t3"></span> Tier 3 (experimental)</span>
    </div>
    <div class="nav-bar">
        {nav_links}
    </div>
    <div class="filter-bar">
        <input type="text" id="filter" placeholder="Filter suites..." oninput="applyFilters()">
        <select id="tierFilter" onchange="applyFilters()">
            <option value="all">All tiers</option>
            <option value="has-t1">Has Tier 1</option>
            <option value="all-t2">All Tier 2+</option>
        </select>
        <label><input type="checkbox" id="hideProfiler" onchange="applyFilters()"> Hide profiling suites</label>
    </div>
</div>

<div class="sticky-banner" id="stickyBanner">
    <h3 id="stickyTitle"></h3>
    <span class="os-stats" id="stickyStats"></span>
</div>
<div class="sticky-cols" id="stickyCols">
    <table><thead><tr id="stickyColRow"></tr></thead></table>
</div>

<div class="content">
    {"".join(os_sections)}

    <div class="variant-section">
        <h2>Variant Tier Overrides</h2>
        <p style="color: #888; font-size: 12px; margin-bottom: 10px;">
            These variants override the base tier when active. Applied on top of the per-platform tiers above.
        </p>
        <table class="variant-table">
            <thead><tr><th>Variant</th><th>Forced Tier</th><th>Applies When</th></tr></thead>
            <tbody>{variant_rows}</tbody>
        </table>
    </div>
</div>

<script>
function applyFilters() {{
    const query = document.getElementById('filter').value.toLowerCase();
    const tierFilter = document.getElementById('tierFilter').value;
    const hideProf = document.getElementById('hideProfiler').checked;
    document.querySelectorAll('.suite-row').forEach(row => {{
        const name = row.dataset.suite.toLowerCase();
        const matchQuery = !query || name.includes(query);
        const matchProf = !hideProf || !name.includes('-profiling');
        let matchTier = true;
        if (tierFilter === 'has-t1') matchTier = row.classList.contains('row-all-t1') || row.classList.contains('row-mixed');
        else if (tierFilter === 'all-t2') matchTier = row.classList.contains('row-all-t2');
        row.classList.toggle('hidden', !(matchQuery && matchTier && matchProf));
    }});
}}

// Sticky OS header + column headers on scroll
(function() {{
    const banner = document.getElementById('stickyBanner');
    const cols = document.getElementById('stickyCols');
    const stickyTitle = document.getElementById('stickyTitle');
    const stickyStats = document.getElementById('stickyStats');
    const stickyColRow = document.getElementById('stickyColRow');
    const topBar = document.querySelector('.top-bar');
    const sections = document.querySelectorAll('.os-section');

    let lastSection = null;

    function updateSticky() {{
        const topBarBottom = topBar.getBoundingClientRect().bottom;
        let active = null;

        sections.forEach(section => {{
            const rect = section.getBoundingClientRect();
            // Section is active if its top is above the sticky zone and bottom is below it
            if (rect.top < topBarBottom + 60 && rect.bottom > topBarBottom + 60) {{
                active = section;
            }}
        }});

        if (active) {{
            const header = active.querySelector('.os-header');
            const thead = active.querySelector('thead');
            const headerRect = header.getBoundingClientRect();
            const theadRect = thead.getBoundingClientRect();

            // Show sticky banner when the real header scrolls above the top bar
            if (headerRect.top < topBarBottom) {{
                banner.style.display = 'block';
                banner.style.top = topBarBottom + 'px';
                const h2 = header.querySelector('h2');
                const stats = header.querySelector('.os-stats');
                stickyTitle.textContent = h2.textContent;
                stickyTitle.style.color = h2.style.color;
                stickyStats.textContent = stats.textContent;

                // Show sticky columns when the real thead scrolls above
                if (theadRect.top < topBarBottom + banner.offsetHeight) {{
                    if (lastSection !== active) {{
                        stickyColRow.innerHTML = thead.querySelector('tr').innerHTML;
                        lastSection = active;
                    }}
                    cols.style.display = 'block';
                    cols.style.top = (topBarBottom + banner.offsetHeight - 1) + 'px';
                    // Match table width
                    const contentTable = active.querySelector('table');
                    cols.querySelector('table').style.maxWidth = contentTable.offsetWidth + 'px';
                }} else {{
                    cols.style.display = 'none';
                }}
            }} else {{
                banner.style.display = 'none';
                cols.style.display = 'none';
                lastSection = null;
            }}
        }} else {{
            banner.style.display = 'none';
            cols.style.display = 'none';
            lastSection = null;
        }}
    }}

    window.addEventListener('scroll', updateSticky, {{ passive: true }});
    window.addEventListener('resize', updateSticky);
}})();
</script>

</body>
</html>'''


def main():
    print("Building tier matrix HTML...")

    suite_tiers = parse_kind_tiers()
    variant_overrides = parse_variant_overrides()
    platforms = get_test_platforms()
    suites = get_all_suites(suite_tiers)

    # Build matrix
    matrix = {}
    for suite in suites:
        matrix[suite] = {}
        for platform in platforms:
            matrix[suite][platform] = resolve_tier(suite, platform, suite_tiers)

    html = build_html(suites, platforms, matrix, variant_overrides, suite_tiers)
    out = BASE / "docs" / "tier_matrix.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Suites: {len(suites)}")
    print(f"  Platforms: {len(platforms)}")
    print(f"  HTML saved to: {out}")


if __name__ == "__main__":
    main()
