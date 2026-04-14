"""
Build a suite x platform tier matrix.

For each suite and each platform, resolves the effective tier (1, 2, or 3)
following the three-layer precedence:
  1. Variant overrides (variants.yml replace: tier:)
  2. Kind task definitions (kinds/test/*.yml tier:)
  3. handle_tier() default (platform-based)

Outputs a JSON matrix and prints a readable summary grouped by OS family.
"""

import re
import yaml
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
FIREFOX = BASE / "firefox"
TC = FIREFOX / "taskcluster"

# --- handle_tier() tier-1 platform list (from other.py) ---

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
    """Resolve tier for suite+platform (without variant)."""
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
    # handle_tier default
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


def main():
    print("Building suite x platform tier matrix...\n")

    suite_tiers = parse_kind_tiers()
    variant_overrides = parse_variant_overrides()
    platforms = get_test_platforms()
    suites = get_all_suites(suite_tiers)

    # Group platforms by OS
    os_groups = defaultdict(list)
    for p in platforms:
        os_groups[platform_os(p)].append(p)

    # Build the full matrix
    matrix = {}
    for suite in suites:
        matrix[suite] = {}
        for platform in platforms:
            matrix[suite][platform] = resolve_tier(suite, platform, suite_tiers)

    # --- Print summary: suite x OS family, showing tier per platform ---
    os_order = ["Linux", "Windows", "macOS", "Android"]

    print(f"{'Suite':<40} ", end="")
    for os_name in os_order:
        print(f"  {os_name:<10}", end="")
    print("  Notes")
    print("-" * 110)

    for suite in suites:
        tiers_by_os = {}
        for os_name in os_order:
            plats = os_groups.get(os_name, [])
            tier_set = set(matrix[suite][p] for p in plats if p in matrix[suite])
            tiers_by_os[os_name] = tier_set

        # Format: show tier if uniform, or "1/2" if mixed
        parts = []
        for os_name in os_order:
            ts = tiers_by_os[os_name]
            if not ts:
                parts.append("  -         ")
            elif len(ts) == 1:
                t = list(ts)[0]
                label = f"T{t}"
                parts.append(f"  {label:<10}")
            else:
                label = "/".join(f"T{t}" for t in sorted(ts))
                parts.append(f"  {label:<10}")

        # Notes
        notes = []
        all_tiers = set()
        for ts in tiers_by_os.values():
            all_tiers.update(ts)
        if all_tiers == {1}:
            notes.append("all T1")
        elif all_tiers == {2}:
            notes.append("all T2")
        elif all_tiers == {3}:
            notes.append("all T3")

        if suite in suite_tiers:
            tier_def = suite_tiers[suite]
            if isinstance(tier_def, int):
                notes.append(f"kind-explicit={tier_def}")
            elif isinstance(tier_def, dict):
                notes.append("kind-keyed")

        print(f"{suite:<40} {''.join(parts)}  {', '.join(notes)}")

    # --- Variant override summary ---
    print(f"\n{'='*110}")
    print("VARIANT TIER OVERRIDES (bump base tier when variant is active):")
    print("-" * 110)
    for name, info in sorted(variant_overrides.items()):
        when_short = info["when"][:70] if isinstance(info["when"], str) else str(info["when"])[:70]
        print(f"  {name:<35} -> tier {info['tier']}  when: {when_short}")

    # --- Save JSON ---
    output = {
        "platforms": platforms,
        "platforms_by_os": {os_name: plats for os_name, plats in os_groups.items()},
        "suites": suites,
        "matrix": matrix,
        "variant_overrides": variant_overrides,
        "suite_tiers_from_kinds": {k: str(v) for k, v in suite_tiers.items()},
    }

    out_path = Path(__file__).parent / "tier_matrix.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nJSON saved to: {out_path}")


if __name__ == "__main__":
    main()
