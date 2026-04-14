"""
Cross-reference tier classification with skip matrix data.

Key question: How many skipped tests are in tier-1 suite+platform combos?
Tier-1 skips matter most — those are tests that should pass before code lands.

The skip matrix tracks skips by OS family (linux, win, mac, android).
The tier system assigns tiers by specific platform (linux2404-64/opt, etc.).
Since tier-1 platforms exist across all 4 OS families, a test skipped on
a given OS is skipped on both tier-1 and tier-2 platforms for that OS.
"""

import re
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
FIREFOX = BASE / "firefox"

OS_LIST = ["linux", "win", "mac", "android"]
OS_DISPLAY = {"linux": "Linux", "win": "Windows", "mac": "macOS", "android": "Android"}

# Map OS family to whether tier-1 platforms exist for that OS
# (from the handle_tier platform list)
TIER1_OS_FAMILIES = {"linux", "win", "mac", "android"}  # all 4 have tier-1 platforms


def infer_suite(rel_path):
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


def extract_os(cond):
    targets = set()
    for m in re.finditer(r"os\s*==\s*['\"](\w+)['\"]", cond):
        targets.add(m.group(1))
    for m in re.finditer(r"os\s*!=\s*['\"](\w+)['\"]", cond):
        targets.update(set(OS_LIST) - {m.group(1)})
    if cond.strip() == "true":
        targets.update(OS_LIST)
    if re.match(r"^(debug|!debug|asan|tsan|verify|ccov)$", cond.strip()):
        targets.update(OS_LIST)
    return targets


def parse_skips():
    """Re-parse skip data from manifests, tracking per-test OS skips and suite."""
    tests = []  # list of {suite, test, manifest, skipped_os: set, skipped_all: bool}

    all_toml = list(FIREFOX.rglob("*.toml"))
    for f in all_toml:
        sf = str(f)
        if "node_modules" in sf or ".git" in sf:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "skip-if" not in content:
            continue

        import os as _os
        rel = str(f.relative_to(FIREFOX)).replace(_os.sep, "/")
        suite = infer_suite(rel)

        # Parse skip conditions
        cur = None
        in_skip = False
        test_skips = defaultdict(set)  # test_name -> set of OS

        for line in content.split("\n"):
            s = line.strip()
            if s.startswith("[") and not s.startswith("[["):
                tm = re.match(r'\["?([^"\]]+)"?\]', s)
                if tm:
                    cur = tm.group(1)
                in_skip = False

            if s.startswith("skip-if"):
                in_skip = True
                il = re.match(r'skip-if\s*=\s*\[(.+)\]', s)
                if il:
                    for c in re.findall(r'"([^"]+)"', il.group(1)):
                        test_skips[cur or "DEFAULT"].update(extract_os(c))
                    in_skip = False
                    continue

            if in_skip:
                if s == "]":
                    in_skip = False
                    continue
                for c in re.findall(r'"([^"]+)"', s):
                    test_skips[cur or "DEFAULT"].update(extract_os(c))

        for test_name, os_set in test_skips.items():
            if test_name == "DEFAULT":
                continue
            tests.append({
                "suite": suite,
                "test": test_name,
                "manifest": rel,
                "skipped_os": os_set,
                "skipped_all": all(o in os_set for o in OS_LIST),
            })

    return tests


def main():
    print("Loading tier classification...")
    tier_data = json.loads(
        (Path(__file__).parent / "tier_classification.json").read_text(encoding="utf-8")
    )

    # Build suite -> tier lookup (simplified: most suites use handle_tier,
    # so tier depends on platform not suite — but some have explicit overrides)
    suite_tier_info = {}
    for s in tier_data["suites"]:
        suite_tier_info[s["suite"]] = {
            "tier_1_count": s["tier_1_platforms"],
            "tier_2_count": s["tier_2_platforms"],
            "tier_3_count": s["tier_3_platforms"],
            "sources": s["sources"],
        }

    # Determine which suites are "always tier 2+" (never tier 1 on any platform)
    always_tier2_suites = set()
    for name, info in suite_tier_info.items():
        if info["tier_1_count"] == 0:
            always_tier2_suites.add(name)

    print("Parsing skip data from manifests...")
    skipped_tests = parse_skips()
    print(f"  Found {len(skipped_tests)} tests with skips\n")

    # --- Cross-reference ---

    # Per-suite summary
    suite_stats = defaultdict(lambda: {
        "total_skipped": 0,
        "skipped_all": 0,
        "tier1_affected": 0,       # tests skipped on at least one OS that has tier-1 platforms
        "tier1_skipped_all": 0,    # tests skipped on ALL platforms (affects tier 1)
        "suite_is_always_t2": False,
        "skips_by_os": defaultdict(int),
    })

    for t in skipped_tests:
        suite = t["suite"]
        stats = suite_stats[suite]
        stats["total_skipped"] += 1
        stats["suite_is_always_t2"] = suite in always_tier2_suites

        if t["skipped_all"]:
            stats["skipped_all"] += 1
            stats["tier1_skipped_all"] += 1

        for os_name in t["skipped_os"]:
            stats["skips_by_os"][os_name] += 1

        # If test is skipped on any OS that has tier-1 platforms, it affects tier 1
        if not stats["suite_is_always_t2"] and t["skipped_os"] & TIER1_OS_FAMILIES:
            stats["tier1_affected"] += 1

    # --- Print results ---

    # Summary table
    print("=" * 100)
    print(f"{'Suite':<35} {'Skipped':>8} {'All-Plat':>9} {'T1-Affected':>12} {'Suite Tier':>10}  {'Linux':>6} {'Win':>6} {'Mac':>6} {'Andr':>6}")
    print("-" * 100)

    total_skipped = 0
    total_all = 0
    total_t1 = 0

    for suite in sorted(suite_stats.keys()):
        s = suite_stats[suite]
        tier_label = "T2+ only" if s["suite_is_always_t2"] else "T1/T2"
        total_skipped += s["total_skipped"]
        total_all += s["skipped_all"]
        total_t1 += s["tier1_affected"]

        print(
            f"{suite:<35} {s['total_skipped']:>8} {s['skipped_all']:>9} "
            f"{s['tier1_affected']:>12} {tier_label:>10}  "
            f"{s['skips_by_os'].get('linux', 0):>6} "
            f"{s['skips_by_os'].get('win', 0):>6} "
            f"{s['skips_by_os'].get('mac', 0):>6} "
            f"{s['skips_by_os'].get('android', 0):>6}"
        )

    print("-" * 100)
    print(f"{'TOTAL':<35} {total_skipped:>8} {total_all:>9} {total_t1:>12}")

    # --- Key insights ---
    print("\n" + "=" * 100)
    print("KEY INSIGHTS:")
    print("-" * 100)

    t1_suites = {s for s in suite_stats if not suite_stats[s]["suite_is_always_t2"]}
    t2_suites = {s for s in suite_stats if suite_stats[s]["suite_is_always_t2"]}

    t1_total_skips = sum(suite_stats[s]["total_skipped"] for s in t1_suites)
    t2_total_skips = sum(suite_stats[s]["total_skipped"] for s in t2_suites)
    t1_all_skips = sum(suite_stats[s]["skipped_all"] for s in t1_suites)

    print(f"  Suites that run as tier 1 (on some platforms): {len(t1_suites)}")
    print(f"  Suites that are always tier 2+:                {len(t2_suites)}")
    print(f"  Skipped tests in tier-1 suites:                {t1_total_skips}")
    print(f"  Skipped tests in tier-2+ only suites:          {t2_total_skips}")
    print(f"  Tier-1 suite tests skipped on ALL platforms:   {t1_all_skips} (complete coverage gaps)")
    print(f"  Tier-1 suite tests skipped on a T1 OS:         {total_t1} (partial coverage gaps on tier-1 platforms)")

    # Save JSON
    output = {
        "summary": {
            "total_skipped_tests": total_skipped,
            "skipped_all_platforms": total_all,
            "tier1_affected_skips": total_t1,
            "tier1_suite_count": len(t1_suites),
            "tier2_only_suite_count": len(t2_suites),
        },
        "suites": {
            suite: {
                "total_skipped": s["total_skipped"],
                "skipped_all_platforms": s["skipped_all"],
                "tier1_affected": s["tier1_affected"],
                "suite_always_tier2": s["suite_is_always_t2"],
                "skips_by_os": dict(s["skips_by_os"]),
            }
            for suite, s in sorted(suite_stats.items())
        },
        "always_tier2_suites": sorted(always_tier2_suites),
    }

    out_path = Path(__file__).parent / "tier_skip_crossref.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nJSON saved to: {out_path}")


if __name__ == "__main__":
    main()
