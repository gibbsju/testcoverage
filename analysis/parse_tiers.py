"""
Parse test suite tier assignments from Firefox CI config.

Tier resolution follows three layers (highest precedence first):
1. Variant overrides (variants.yml replace: tier:) — forces tier for specific variant+suite combos
2. Kind task definitions (kinds/test/*.yml tier:) — suite-level, sometimes keyed by-test-platform
3. handle_tier() default (other.py) — platform-based: hardcoded list → tier 1, everything else → tier 2

Suites not explicitly listed in kind YAML files (mochitest-plain, mochitest-browser-chrome, etc.)
are auto-discovered from test manifests and have no explicit tier, so they always use handle_tier().
"""

import re
import yaml
import json
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent
FIREFOX = BASE / "firefox"
TC = FIREFOX / "taskcluster"

# --- Layer 3: handle_tier() default platforms ---

TIER_1_PLATFORMS = [
    "linux64/opt",
    "linux64/debug",
    "linux64-shippable/opt",
    "linux64-devedition/opt",
    "linux64-asan/opt",
    "linux64-qr/opt",
    "linux64-qr/debug",
    "linux64-shippable-qr/opt",
    "linux2204-64-wayland/debug",
    "linux2204-64-wayland/opt",
    "linux2204-64-wayland-shippable/opt",
    "linux2404-64/opt",
    "linux2404-64/debug",
    "linux2404-64-shippable/opt",
    "linux2404-64-devedition/opt",
    "linux2404-64-asan/opt",
    "linux2404-64-tsan/opt",
    "windows11-32-24h2/debug",
    "windows11-32-24h2/opt",
    "windows11-32-24h2-shippable/opt",
    "windows11-64-24h2-hw-ref/opt",
    "windows11-64-24h2-hw-ref-shippable/opt",
    "windows11-64-24h2/opt",
    "windows11-64-24h2/debug",
    "windows11-64-24h2-shippable/opt",
    "windows11-64-24h2-devedition/opt",
    "windows11-64-24h2-asan/opt",
    "macosx1015-64/opt",
    "macosx1015-64/debug",
    "macosx1015-64-shippable/opt",
    "macosx1015-64-devedition/opt",
    "macosx1015-64-devedition-qr/opt",
    "macosx1015-64-qr/opt",
    "macosx1015-64-shippable-qr/opt",
    "macosx1015-64-qr/debug",
    "macosx1470-64/opt",
    "macosx1470-64/debug",
    "macosx1470-64-shippable/opt",
    "macosx1470-64-devedition/opt",
    "macosx1400-64-shippable-qr/opt",
    "macosx1400-64-qr/debug",
    "macosx1500-64-shippable/opt",
    "macosx1500-64/debug",
    "android-em-14-x86_64-shippable/opt",
    "android-em-14-x86_64/opt",
    "android-em-14-x86_64-shippable-lite/opt",
    "android-em-14-x86_64-lite/opt",
    "android-em-14-x86_64/debug",
    "android-em-14-x86_64/debug-isolated-process",
    "android-em-14-x86-shippable/opt",
    "android-em-14-x86/opt",
]

# Classify platforms into OS families for summary
def platform_os(platform):
    if platform.startswith("linux"):
        return "linux"
    elif platform.startswith("windows"):
        return "windows"
    elif platform.startswith("macosx"):
        return "macos"
    elif platform.startswith("android"):
        return "android"
    return "other"


# --- Layer 2: Kind YAML tier definitions ---

def parse_kind_tiers():
    """Parse tier: fields from kinds/test/*.yml files.
    Returns {suite_name: tier_value} where tier_value is:
      - int (explicit tier)
      - "default" (falls through to handle_tier)
      - dict with by-test-platform keys
    """
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


# --- Layer 1: Variant tier overrides ---

def parse_variant_overrides():
    """Parse replace: tier: from variants.yml.
    Returns {variant_name: {"tier": int, "when": str_description}}
    """
    variants_file = TC / "test_configs" / "variants.yml"
    data = yaml.safe_load(variants_file.read_text(encoding="utf-8"))

    overrides = {}
    for variant_name, variant_def in data.items():
        if not isinstance(variant_def, dict):
            continue
        replace = variant_def.get("replace", {})
        if isinstance(replace, dict) and "tier" in replace:
            when_expr = variant_def.get("when", {}).get("$eval", "always")
            overrides[variant_name] = {
                "tier": replace["tier"],
                "when": when_expr,
                "suffix": variant_def.get("suffix", variant_name),
            }

    return overrides


# --- Resolve tier for suite+platform ---

def resolve_tier(suite, platform, suite_tiers, variant=None, variant_overrides=None):
    """Resolve the effective tier for a suite on a platform, optionally with a variant."""

    # Layer 1: variant override (highest precedence)
    if variant and variant_overrides and variant in variant_overrides:
        return variant_overrides[variant]["tier"], f"variant-{variant}"

    # Layer 2: kind YAML tier
    if suite in suite_tiers:
        tier_def = suite_tiers[suite]

        if isinstance(tier_def, int):
            return tier_def, "kind-explicit"

        if isinstance(tier_def, dict) and "by-test-platform" in tier_def:
            keyed = tier_def["by-test-platform"]
            for pattern, value in keyed.items():
                if pattern == "default":
                    continue
                if re.match(pattern, platform):
                    if isinstance(value, int):
                        return value, f"kind-keyed({pattern})"
                    # value is "default", fall through
                    break
            # Check default
            default_val = keyed.get("default", "default")
            if isinstance(default_val, int):
                return default_val, "kind-keyed(default)"
            # "default" string → fall through to handle_tier

        if tier_def == "default":
            pass  # fall through to handle_tier

    # Layer 3: handle_tier() default
    if platform in TIER_1_PLATFORMS:
        return 1, "handle_tier"
    return 2, "handle_tier"


# --- Get all test platforms ---

def get_test_platforms():
    """Parse test-platforms.yml to get all platform names."""
    tp_file = TC / "test_configs" / "test-platforms.yml"
    data = yaml.safe_load(tp_file.read_text(encoding="utf-8"))
    return list(data.keys()) if data else []


# --- Get test sets (suite groupings) ---

def get_test_sets():
    """Parse test-sets.yml to get suite names grouped into test sets."""
    ts_file = TC / "test_configs" / "test-sets.yml"
    data = yaml.safe_load(ts_file.read_text(encoding="utf-8"))
    all_suites = set()
    if data:
        for test_set, suites in data.items():
            if isinstance(suites, list):
                all_suites.update(suites)
    return sorted(all_suites)


def main():
    print("Parsing tier configuration...\n")

    suite_tiers = parse_kind_tiers()
    variant_overrides = parse_variant_overrides()
    platforms = get_test_platforms()
    suites_from_sets = get_test_sets()

    # Also include suites from kind YAMLs that aren't in test-sets
    all_suites = sorted(set(suites_from_sets) | set(suite_tiers.keys()))

    print(f"Platforms: {len(platforms)}")
    print(f"Suites (from test-sets + kinds): {len(all_suites)}")
    print(f"Variant tier overrides: {len(variant_overrides)}")

    # --- Build per-suite tier summary ---
    print("\n" + "=" * 80)
    print(f"{'Suite':<40} {'Tier 1 plats':>12} {'Tier 2 plats':>12} {'Tier 3 plats':>12} {'Source':<20}")
    print("-" * 80)

    results = []
    for suite in all_suites:
        tier_counts = defaultdict(int)
        sources = set()
        platform_tiers = {}

        for platform in platforms:
            tier, source = resolve_tier(suite, platform, suite_tiers)
            tier_counts[tier] += 1
            sources.add(source)
            platform_tiers[platform] = {"tier": tier, "source": source}

        source_str = ", ".join(sorted(sources))
        t1 = tier_counts.get(1, 0)
        t2 = tier_counts.get(2, 0)
        t3 = tier_counts.get(3, 0)

        print(f"{suite:<40} {t1:>12} {t2:>12} {t3:>12} {source_str:<20}")

        results.append({
            "suite": suite,
            "tier_1_platforms": t1,
            "tier_2_platforms": t2,
            "tier_3_platforms": t3,
            "sources": list(sorted(sources)),
            "platform_details": platform_tiers,
        })

    # --- Variant overrides summary ---
    print("\n" + "=" * 80)
    print("VARIANT TIER OVERRIDES (applied on top of base tier):")
    print("-" * 80)
    for name, info in sorted(variant_overrides.items()):
        print(f"  {name:<30} -> tier {info['tier']}  (when: {info['when'][:60]})")

    # --- Write JSON output ---
    output = {
        "tier_1_platforms": TIER_1_PLATFORMS,
        "variant_overrides": variant_overrides,
        "suite_tiers_from_kinds": {k: str(v) for k, v in suite_tiers.items()},
        "suites": results,
    }

    out_path = Path(__file__).parent / "tier_classification.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nJSON saved to: {out_path}")


if __name__ == "__main__":
    main()
