"""
Parse Firefox test manifests to build a skip matrix.

Scans .toml and .ini manifest files for skip-if annotations,
extracts the conditions, and maps them to OS/platform.

Outputs:
  - Which tests are skipped on which OS/platform
  - Tests skipped on ALL platforms (dangerous coverage gaps)
  - Skip counts by OS and condition type
"""

import re
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
FIREFOX = BASE / "firefox"

# OS values used in skip-if conditions
OS_VALUES = {"linux", "win", "mac", "android"}


def extract_skip_conditions_toml(filepath):
    """Extract skip-if conditions from a TOML manifest file.

    Returns list of (test_name, condition_string) tuples.
    """
    results = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return results

    current_test = None
    in_skip_if = False
    skip_lines = []

    for line in content.split("\n"):
        stripped = line.strip()

        # Track current test section
        if stripped.startswith("[") and not stripped.startswith("[["):
            test_match = re.match(r'\["?([^"\]]+)"?\]', stripped)
            if test_match:
                current_test = test_match.group(1)
            in_skip_if = False
            skip_lines = []

        # Detect skip-if start
        if stripped.startswith("skip-if"):
            in_skip_if = True
            skip_lines = []
            # Check for inline value
            inline = re.match(r'skip-if\s*=\s*\[(.+)\]', stripped)
            if inline:
                for cond in re.findall(r'"([^"]+)"', inline.group(1)):
                    results.append((current_test or "DEFAULT", cond, str(filepath)))
                in_skip_if = False
            elif "=" in stripped and "[" in stripped:
                # Multi-line array starts
                pass
            continue

        if in_skip_if:
            if stripped == "]":
                in_skip_if = False
                continue
            # Extract quoted condition strings
            for cond in re.findall(r'"([^"]+)"', stripped):
                results.append((current_test or "DEFAULT", cond, str(filepath)))

    return results


def extract_os_from_condition(condition):
    """Extract which OS(es) a skip condition targets."""
    targets = set()

    # Simple "os == 'xxx'" pattern
    for os_match in re.finditer(r"os\s*==\s*['\"](\w+)['\"]", condition):
        targets.add(os_match.group(1))

    # "os != 'xxx'" means skip on everything EXCEPT that OS
    for os_match in re.finditer(r"os\s*!=\s*['\"](\w+)['\"]", condition):
        excluded = os_match.group(1)
        targets.update(OS_VALUES - {excluded})

    # Unconditional skip
    if condition.strip() == "true":
        targets.update(OS_VALUES)

    # Build-type only conditions (no OS specified) apply to all
    build_only_patterns = [
        r"^debug$", r"^!debug$", r"^asan$", r"^tsan$", r"^verify",
        r"^ccov$", r"^!is_",
    ]
    if not targets:
        for pattern in build_only_patterns:
            if re.match(pattern, condition.strip()):
                targets.update(OS_VALUES)
                break

    return targets


def extract_extra_info(condition):
    """Extract additional context from a condition."""
    info = {}
    if "os_version" in condition:
        for m in re.finditer(r"os_version\s*==\s*['\"]([^'\"]+)['\"]", condition):
            info["os_version"] = m.group(1)
    if "display" in condition:
        for m in re.finditer(r"display\s*==\s*['\"]([^'\"]+)['\"]", condition):
            info["display"] = m.group(1)
    if "arch" in condition:
        for m in re.finditer(r"arch\s*==\s*['\"]([^'\"]+)['\"]", condition):
            info["arch"] = m.group(1)
    return info


def find_manifest_files():
    """Find all test manifest files in the Firefox repo."""
    manifests = []
    # Common manifest patterns
    for pattern in ["**/xpcshell.toml", "**/browser.toml", "**/mochitest.toml",
                    "**/chrome.toml", "**/a11y.toml", "**/crashtest.toml",
                    "**/reftest.toml", "**/*.toml"]:
        for f in FIREFOX.glob(pattern):
            if f not in manifests and "node_modules" not in str(f):
                manifests.append(f)
    return manifests


def build_skip_matrix():
    print("Finding manifest files...")
    # Use a more targeted approach - find all .toml files that contain skip-if
    all_toml = list(FIREFOX.rglob("*.toml"))
    # Filter to only test manifests (those containing skip-if or test definitions)
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

    print(f"  Found {len(manifests)} manifest files with skip-if annotations")
    print(f"  (out of {len(all_toml)} total .toml files)")

    # Extract all skip conditions
    print("\nExtracting skip conditions...")
    all_skips = []
    for mf in manifests:
        skips = extract_skip_conditions_toml(mf)
        all_skips.extend(skips)
    print(f"  Found {len(all_skips)} skip-if entries")

    # Analyze by OS
    print("\nAnalyzing skip targets by OS...")
    os_skip_counts = defaultdict(int)
    test_os_skips = defaultdict(lambda: defaultdict(list))  # test -> os -> [conditions]
    unconditional_skips = []
    unresolved_skips = []

    for test_name, condition, filepath in all_skips:
        # Make a relative path key
        rel_path = str(Path(filepath).relative_to(FIREFOX))
        test_key = f"{rel_path}::{test_name}"

        targets = extract_os_from_condition(condition)
        extra = extract_extra_info(condition)

        if condition.strip() == "true":
            unconditional_skips.append((test_key, condition, filepath))

        if not targets:
            unresolved_skips.append((test_key, condition))
        else:
            for os_name in targets:
                os_skip_counts[os_name] += 1
                test_os_skips[test_key][os_name].append({
                    "condition": condition,
                    "extra": extra,
                })

    # Find tests skipped on ALL platforms
    print("\nFinding tests skipped on ALL platforms...")
    skipped_everywhere = []
    for test_key, os_map in test_os_skips.items():
        if OS_VALUES.issubset(os_map.keys()):
            skipped_everywhere.append(test_key)

    return {
        "total_manifests": len(manifests),
        "total_skip_entries": len(all_skips),
        "os_skip_counts": dict(os_skip_counts),
        "unconditional_skips": unconditional_skips,
        "skipped_everywhere": sorted(skipped_everywhere),
        "skipped_everywhere_count": len(skipped_everywhere),
        "unresolved_count": len(unresolved_skips),
        "unresolved_sample": unresolved_skips[:20],
        "test_os_skips": {k: dict(v) for k, v in test_os_skips.items()},
    }


def print_skip_report(results):
    print(f"\n{'=' * 80}")
    print("SKIP MATRIX REPORT")
    print(f"{'=' * 80}")

    print(f"\n  Manifests with skip-if: {results['total_manifests']}")
    print(f"  Total skip-if entries:  {results['total_skip_entries']}")

    print(f"\n  Skip counts by OS:")
    for os_name in sorted(results["os_skip_counts"].keys()):
        count = results["os_skip_counts"][os_name]
        print(f"    {os_name:10s}: {count} skips")

    print(f"\n  Unconditional skips (skip-if = true): {len(results['unconditional_skips'])}")
    if results["unconditional_skips"]:
        for test_key, cond, fp in results["unconditional_skips"][:15]:
            print(f"    - {test_key}")
        if len(results["unconditional_skips"]) > 15:
            print(f"    ... and {len(results['unconditional_skips']) - 15} more")

    print(f"\n  Unresolved conditions (couldn't map to OS): {results['unresolved_count']}")
    if results["unresolved_sample"]:
        print(f"  Sample unresolved conditions:")
        for test_key, cond in results["unresolved_sample"][:10]:
            print(f"    - {cond[:80]}")

    print(f"\n{'=' * 80}")
    print(f"TESTS SKIPPED ON ALL PLATFORMS ({results['skipped_everywhere_count']} tests)")
    print(f"  >>> These are DANGEROUS coverage gaps <<<")
    print(f"{'=' * 80}")
    for test_key in results["skipped_everywhere"][:50]:
        print(f"  - {test_key}")
    if results["skipped_everywhere_count"] > 50:
        print(f"  ... and {results['skipped_everywhere_count'] - 50} more")


def save_skip_json(results):
    # Save a summary (full test_os_skips can be huge)
    summary = {
        "total_manifests": results["total_manifests"],
        "total_skip_entries": results["total_skip_entries"],
        "os_skip_counts": results["os_skip_counts"],
        "unconditional_skip_count": len(results["unconditional_skips"]),
        "unconditional_skips": [(t, c) for t, c, f in results["unconditional_skips"]],
        "skipped_everywhere": results["skipped_everywhere"],
        "skipped_everywhere_count": results["skipped_everywhere_count"],
        "unresolved_count": results["unresolved_count"],
    }

    out_path = BASE / "docs" / "skip_matrix.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nJSON output saved to: {out_path}")


if __name__ == "__main__":
    results = build_skip_matrix()
    print_skip_report(results)
    save_skip_json(results)
