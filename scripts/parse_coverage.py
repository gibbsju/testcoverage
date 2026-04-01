"""
Parse Firefox CI config files to build a pool-to-test-suite coverage map.

Resolves worker-types at the (platform, suite) level, since performance suites
(talos, raptor/browsertime) route to dedicated hardware pools while functional
tests run on VMs.

Reads:
  - firefox/taskcluster/test_configs/test-platforms.yml
  - firefox/taskcluster/test_configs/test-sets.yml
  - firefox/taskcluster/gecko_taskgraph/transforms/test/worker.py (logic extracted)
  - firefox/taskcluster/kinds/test/*.yml and kinds/browsertime/*.yml (suite metadata)
  - fxci-config/worker-pools.yml
"""

import yaml
import re
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent  # scripts/ is one level down from project root
FIREFOX = BASE / "firefox"
FXCI = BASE / "fxci-config"

# From gecko_taskgraph/transforms/test/worker.py
LINUX_WORKER_TYPES = {
    "large-legacy": "t-linux-docker",
    "large": "t-linux-docker-amd",
    "large-noscratch": "t-linux-docker-noscratch-amd",
    "xlarge": "t-linux-docker-amd",
    "xlarge-noscratch": "t-linux-docker-noscratch-amd",
    "highcpu": "t-linux-docker-16c32gb-amd",
    "default": "t-linux-docker-noscratch-amd",
}

MACOSX_WORKER_TYPES = {
    "macosx1015-64": "t-osx-1015-r8",
    "macosx1470-64": "t-osx-1400-r8",
    "macosx1400-64": "t-osx-1400-m2",
    "macosx1500-64": "t-osx-1500-m4",
    "macosx1500-aarch64": "t-osx-1500-m4",
}

WINDOWS_WORKER_TYPES = {
    "windows10-64-2009": {"virtual": "win10-64-2009", "virtual-with-gpu": "win10-64-2009-gpu", "hardware": "win10-64-2009-hw"},
    "windows10-64-2009-qr": {"virtual": "win10-64-2009", "virtual-with-gpu": "win10-64-2009-gpu", "hardware": "win10-64-2009-hw"},
    "windows10-64-2009-shippable-qr": {"virtual": "win10-64-2009", "virtual-with-gpu": "win10-64-2009-gpu", "hardware": "win10-64-2009-hw"},
    "windows11-32-24h2": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu"},
    "windows11-32-24h2-shippable": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu"},
    "windows11-32-24h2-mingwclang": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu"},
    "windows11-64-24h2": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu", "hardware": "win11-64-24h2-hw"},
    "windows11-64-24h2-shippable": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu", "hardware": "win11-64-24h2-hw"},
    "windows11-64-24h2-ccov": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu"},
    "windows11-64-24h2-devedition": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu"},
    "windows11-64-24h2-asan": {"virtual": "win11-64-24h2", "large": "win11-64-24h2-large", "virtual-with-gpu": "win11-64-24h2-gpu"},
    "windows11-64-24h2-mingwclang": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu"},
    "windows11-64-24h2-nightlyasrelease": {"virtual": "win11-64-24h2", "virtual-with-gpu": "win11-64-24h2-gpu", "hardware": "win11-64-24h2-hw"},
    "windows11-64-24h2-hw-ref": {"virtual": "win11-64-24h2-hw-ref", "virtual-with-gpu": "win11-64-24h2-hw-ref", "hardware": "win11-64-24h2-hw-ref"},
    "windows11-64-24h2-hw-ref-shippable": {"virtual": "win11-64-24h2-hw-ref", "virtual-with-gpu": "win11-64-24h2-hw-ref", "hardware": "win11-64-24h2-hw-ref"},
    "windows11-aarch64-24h2": {"virtual": "win11-a64-24h2"},
    "windows11-aarch64-24h2-devedition": {"virtual": "win11-a64-24h2"},
    "windows11-aarch64-24h2-shippable": {"virtual": "win11-a64-24h2"},
}

ANDROID_HW_WORKER_TYPES = {
    "android-hw-p5": "t-bitbar-gw-unit-p5",
    "android-hw-p6": "t-bitbar-gw-unit-p6",
    "android-hw-s24": "t-bitbar-gw-unit-s24",
    "android-hw-a55": "t-lambda-perf-a55",
}

# Suites that use "hardware" virtualization (from kinds/test/talos.yml and kinds/browsertime/)
# talos-xperf is the one exception (virtual, Windows admin-only)
HARDWARE_SUITES = set()
VIRTUAL_WITH_GPU_SUITES = set()

# Talos suites — all hardware except talos-xperf
TALOS_SUITES = {
    "talos-bcv", "talos-bcv-profiling", "talos-chrome", "talos-chrome-profiling",
    "talos-damp-inspector", "talos-damp-other", "talos-damp-webconsole",
    "talos-dromaeojs", "talos-dromaeojs-profiling",
    "talos-g1", "talos-g1-profiling", "talos-g3", "talos-g3-profiling",
    "talos-g4", "talos-g4-profiling", "talos-g5", "talos-g5-profiling",
    "talos-motionmark-profiling", "talos-other", "talos-other-profiling",
    "talos-pdfpaint", "talos-perf-reftest", "talos-perf-reftest-profiling",
    "talos-perf-reftest-singletons", "talos-perf-reftest-singletons-profiling",
    "talos-realworld-webextensions", "talos-realworld-webextensions-profiling",
    "talos-sessionrestore-many-windows", "talos-sessionrestore-many-windows-profiling",
    "talos-svgr", "talos-svgr-profiling",
    "talos-tabswitch", "talos-tabswitch-profiling",
    "talos-tp5o", "talos-tp5o-profiling",
    "talos-webgl", "talos-webgl-profiling",
}
HARDWARE_SUITES.update(TALOS_SUITES)

# Browsertime/Raptor — all hardware
BROWSERTIME_SUITES = {
    "browsertime-tp6", "browsertime-tp6-essential", "browsertime-tp6-bytecode",
    "browsertime-tp6-live", "browsertime-tp6-live-sheriffed", "browsertime-tp6-profiling",
    "browsertime-tp6-webextensions", "browsertime-tp7",
    "browsertime-benchmark", "browsertime-benchmark-wasm",
    "browsertime-responsiveness", "browsertime-custom", "browsertime-first-install",
    "browsertime-youtube-playback", "browsertime-youtube-playback-power",
    "browsertime-network-bench", "browsertime-pageload-benchmark",
    "browsertime-regression-tests", "browsertime-speculative", "browsertime-throttled",
    "browsertime-indexeddb", "browsertime-upload", "browsertime-webcodecs",
    "browsertime-trr-performance", "browsertime-video-playback-latency",
    # Mobile
    "browsertime-tp6m", "browsertime-tp6m-essential", "browsertime-tp6m-live",
    "browsertime-tp6m-profiling", "browsertime-tp6m-webextensions",
    "browsertime-benchmark-speedometer2-mobile", "browsertime-benchmark-speedometer3-mobile",
    "browsertime-benchmark-unity-webgl-mobile", "browsertime-benchmark-motionmark-1-3",
    "browsertime-benchmark-jetstream2", "browsertime-benchmark-jetstream3",
    "browsertime-youtube-playback-mobile", "browsertime-youtube-playback-power-mobile",
    "browsertime-video-playback-latency-mobile", "browsertime-trr-performance-m",
}
HARDWARE_SUITES.update(BROWSERTIME_SUITES)

# talos-xperf is virtual (Windows admin-only, uses privileged pool)
VIRTUAL_HARDWARE_EXCEPTIONS = {"talos-xperf"}

# GPU suites
VIRTUAL_WITH_GPU_SUITES = {"test-verify-gpu", "mochitest-webgpu"}


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_kinds_worker_type_overrides():
    """Parse kinds/test/*.yml and other test kind files for worker-type overrides.

    These overrides take precedence over worker.py logic. Returns a list of:
      (suite_names_set, regex_pattern, worker_type, source_file)

    For task-defaults overrides, suite_names_set contains all suites defined in that file.
    For per-suite overrides, it contains just that suite.
    """
    overrides = []
    kinds_dirs = [
        FIREFOX / "taskcluster/kinds/test",
        FIREFOX / "taskcluster/kinds/web-platform-tests",
        FIREFOX / "taskcluster/kinds/mochitest",
        FIREFOX / "taskcluster/kinds/reftest",
        FIREFOX / "taskcluster/kinds/browsertime",
    ]

    for kinds_dir in kinds_dirs:
        if not kinds_dir.exists():
            continue
        for yml_file in kinds_dir.glob("*.yml"):
            try:
                data = load_yaml(yml_file)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            # Collect all suite names defined in this file
            file_suites = set()
            for key, val in data.items():
                if key not in ("task-defaults", "tasks-from", "loader",
                               "kind-dependencies", "transforms") and isinstance(val, dict):
                    file_suites.add(key)

            # Check task-defaults for worker-type overrides
            # These apply ONLY to suites defined in this same file
            defaults = data.get("task-defaults", {})
            if isinstance(defaults, dict):
                wt = defaults.get("worker-type")
                if isinstance(wt, dict) and "by-test-platform" in wt:
                    for pattern, worker_type in wt["by-test-platform"].items():
                        if isinstance(worker_type, str) and worker_type != "default":
                            overrides.append((file_suites, pattern, worker_type, yml_file.name))
                elif isinstance(wt, dict):
                    for variant_key, variant_val in wt.items():
                        if isinstance(variant_val, dict) and "by-test-platform" in variant_val:
                            for pattern, worker_type in variant_val["by-test-platform"].items():
                                if isinstance(worker_type, str) and worker_type != "default":
                                    overrides.append((file_suites, pattern, worker_type, yml_file.name))

            # Check individual suite definitions for worker-type overrides
            for suite_name, suite_config in data.items():
                if suite_name in ("task-defaults", "tasks-from") or not isinstance(suite_config, dict):
                    continue
                wt = suite_config.get("worker-type")
                if isinstance(wt, str) and wt != "default":
                    overrides.append(({suite_name}, ".*", wt, yml_file.name))
                elif isinstance(wt, dict) and "by-test-platform" in wt:
                    for pattern, worker_type in wt["by-test-platform"].items():
                        if isinstance(worker_type, str) and worker_type != "default":
                            overrides.append(({suite_name}, pattern, worker_type, yml_file.name))

    return overrides


_KINDS_OVERRIDES = None


def get_kinds_overrides():
    global _KINDS_OVERRIDES
    if _KINDS_OVERRIDES is None:
        _KINDS_OVERRIDES = parse_kinds_worker_type_overrides()
    return _KINDS_OVERRIDES


def check_kinds_override(test_platform, suite_name):
    """Check if a kinds override applies for this (platform, suite).

    Returns the worker-type string if found, None otherwise.
    Only matches if the suite is in the set of suites the override applies to.
    """
    overrides = get_kinds_overrides()

    for applicable_suites, pattern, worker_type, source in overrides:
        if suite_name in applicable_suites:
            try:
                if re.match(pattern, test_platform):
                    return worker_type
            except re.error:
                continue

    return None


def parse_test_platforms():
    data = load_yaml(FIREFOX / "taskcluster/test_configs/test-platforms.yml")
    platforms = {}
    for platform_name, config in data.items():
        if isinstance(config, dict) and "test-sets" in config:
            platforms[platform_name] = {
                "build-platform": config.get("build-platform", ""),
                "test-sets": config["test-sets"],
            }
    return platforms


def parse_test_sets():
    data = load_yaml(FIREFOX / "taskcluster/test_configs/test-sets.yml")
    return {k: v for k, v in data.items() if isinstance(v, list)}


def get_suite_harness(suite_name):
    """Determine what harness category a suite belongs to."""
    if suite_name in TALOS_SUITES:
        return "talos"
    if suite_name in BROWSERTIME_SUITES:
        return "raptor"
    if suite_name.startswith("talos-"):
        return "talos"
    if suite_name.startswith("browsertime-"):
        return "raptor"
    if suite_name.startswith("awsy"):
        return "awsy"
    return "functional"


def get_virtualization(suite_name):
    """Determine virtualization type for a suite."""
    if suite_name in VIRTUAL_HARDWARE_EXCEPTIONS:
        return "virtual"
    if suite_name in HARDWARE_SUITES:
        return "hardware"
    if suite_name in VIRTUAL_WITH_GPU_SUITES:
        return "virtual-with-gpu"
    return "virtual"


def resolve_worker_type(test_platform, suite_name, build_platform=""):
    """Resolve a (platform, suite) pair to its worker-type.

    Priority:
      1. Kinds overrides (from kinds/test/*.yml etc.) — highest priority
      2. worker.py logic — fallback
    """
    # Check kinds overrides first — they take precedence
    kinds_wt = check_kinds_override(test_platform, suite_name)
    if kinds_wt is not None:
        return kinds_wt

    platform_base = test_platform.split("/")[0]
    virtualization = get_virtualization(suite_name)
    harness = get_suite_harness(suite_name)
    is_perf = harness in ("talos", "raptor")

    # macOS — same worker-type regardless of suite type
    for prefix, wt in MACOSX_WORKER_TYPES.items():
        if test_platform.startswith(prefix):
            return wt

    # Windows
    if test_platform.startswith("win"):
        if platform_base in WINDOWS_WORKER_TYPES:
            wt_map = WINDOWS_WORKER_TYPES[platform_base]
            if virtualization == "hardware" and "hardware" in wt_map:
                return wt_map["hardware"]
            return wt_map.get(virtualization, wt_map.get("virtual", "unknown-win"))
        return "unknown-win-platform"

    # Android hardware
    for prefix, wt in ANDROID_HW_WORKER_TYPES.items():
        if test_platform.startswith(prefix):
            return wt

    # Android emulator
    if test_platform.startswith("android-em-"):
        return "t-linux-kvm"

    # Linux with wayland
    if test_platform.startswith("linux") and "wayland" in test_platform:
        return "t-linux-wayland"

    # Linux — perf suites go to moonshot hardware
    if test_platform.startswith("linux") or test_platform.startswith("android"):
        if is_perf and not build_platform.startswith("linux64-ccov"):
            if test_platform.startswith("linux2404"):
                if "browsertime-network-bench" == suite_name:
                    return "t-linux-netperf-2404"
                return "t-linux-talos-2404"
            else:
                if "browsertime-network-bench" == suite_name:
                    return "t-linux-netperf-1804"
                return "t-linux-talos-1804"
        return LINUX_WORKER_TYPES["default"]

    return "unknown"


def parse_worker_pools():
    data = load_yaml(FXCI / "worker-pools.yml")
    pools = {}
    for pool_entry in data.get("pools", []):
        pool_id = pool_entry.get("pool_id", "")
        variants = pool_entry.get("variants", [])
        provider = pool_entry.get("provider_id", "")
        if isinstance(provider, dict):
            provider = str(provider)
        if variants:
            for variant in variants:
                expanded_id = pool_id
                for key, val in variant.items():
                    expanded_id = expanded_id.replace(f"{{{key}}}", str(val))
                expanded_id = re.sub(r'\{[^}]*\}', '', expanded_id)
                pools[expanded_id] = {
                    "description": pool_entry.get("description", ""),
                    "provider_id": provider,
                    "is_alpha": "alpha" in expanded_id.lower(),
                }
        else:
            pools[pool_id] = {
                "description": pool_entry.get("description", ""),
                "provider_id": provider,
                "is_alpha": "alpha" in pool_id.lower(),
            }
    return pools


def classify_os(name):
    if "linux" in name:
        return "Linux"
    elif "windows" in name or "win" in name:
        return "Windows"
    elif "macosx" in name or "osx" in name:
        return "macOS"
    elif "android" in name or "bitbar" in name or "lambda" in name:
        return "Android"
    return "Other"


def build_coverage_map():
    print("Parsing test-platforms.yml...")
    platforms = parse_test_platforms()
    print(f"  Found {len(platforms)} test platforms")

    print("Parsing test-sets.yml...")
    test_sets = parse_test_sets()
    print(f"  Found {len(test_sets)} test sets")

    print("Parsing worker-pools.yml...")
    worker_pools = parse_worker_pools()
    print(f"  Found {len(worker_pools)} expanded pools")

    print("Parsing kinds worker-type overrides...")
    overrides = get_kinds_overrides()
    print(f"  Found {len(overrides)} override rules")

    # Resolve each (platform, suite) -> worker-type
    print("\nResolving (platform, suite) -> worker-type...")
    # Structure: worker_type -> {platforms: set, suites: set, suite_details: [(platform, suite)]}
    wt_coverage = defaultdict(lambda: {"platforms": set(), "suites": set(), "assignments": []})

    platform_suites = {}
    for platform_name, config in platforms.items():
        suites = set()
        for test_set_name in config["test-sets"]:
            if test_set_name in test_sets:
                suites.update(test_sets[test_set_name])
        platform_suites[platform_name] = sorted(suites)

        build_platform = config.get("build-platform", "")
        for suite in suites:
            wt = resolve_worker_type(platform_name, suite, build_platform)
            wt_coverage[wt]["platforms"].add(platform_name)
            wt_coverage[wt]["suites"].add(suite)
            wt_coverage[wt]["assignments"].append((platform_name, suite))

    # Convert sets for display
    for wt in wt_coverage:
        wt_coverage[wt]["platforms"] = sorted(wt_coverage[wt]["platforms"])
        wt_coverage[wt]["suites"] = sorted(wt_coverage[wt]["suites"])

    return wt_coverage, platform_suites, worker_pools


def print_coverage_report(wt_coverage, platform_suites, worker_pools):
    print("=" * 80)
    print("WORKER-TYPE COVERAGE MAP")
    print("  (resolves per platform+suite, accounting for hardware vs VM routing)")
    print("=" * 80)

    os_families = {"Linux": [], "Windows": [], "macOS": [], "Android": []}
    for wt, data in sorted(wt_coverage.items()):
        os_name = classify_os(wt)
        if os_name == "Other" and data["platforms"]:
            os_name = classify_os(data["platforms"][0])
        os_families.get(os_name, os_families["Linux"]).append((wt, data))

    for os_name, entries in os_families.items():
        if not entries:
            continue
        print(f"\n{'-' * 80}")
        print(f"  {os_name}")
        print(f"{'-' * 80}")

        for wt, data in entries:
            is_alpha = "alpha" in wt.lower()
            tag = " [ALPHA/GREENING]" if is_alpha else ""

            # Classify suites by type
            perf_suites = [s for s in data["suites"] if get_suite_harness(s) in ("talos", "raptor")]
            func_suites = [s for s in data["suites"] if get_suite_harness(s) == "functional"]
            other_suites = [s for s in data["suites"] if get_suite_harness(s) == "awsy"]

            print(f"\n  Worker-type: {wt}{tag}")
            print(f"  Platforms ({len(data['platforms'])}): {', '.join(sorted(data['platforms']))}")
            print(f"  Total suites: {len(data['suites'])}")
            if perf_suites:
                print(f"    Performance ({len(perf_suites)}): {', '.join(perf_suites[:5])}{'...' if len(perf_suites) > 5 else ''}")
            if func_suites:
                print(f"    Functional ({len(func_suites)}): {', '.join(func_suites[:5])}{'...' if len(func_suites) > 5 else ''}")
            if other_suites:
                print(f"    Other ({len(other_suites)}): {', '.join(other_suites)}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Total test platforms: {len(platform_suites)}")
    print(f"  Total worker-types: {len(wt_coverage)}")
    all_suites = set()
    for data in wt_coverage.values():
        all_suites.update(data["suites"])
    print(f"  Total unique suites: {len(all_suites)}")

    os_counts = defaultdict(int)
    for p in platform_suites:
        os_counts[classify_os(p)] += 1
    print(f"\n  Per-OS platform count:")
    for os_name, count in sorted(os_counts.items()):
        print(f"    {os_name}: {count} platforms")

    # Worker-type categories
    print(f"\n  Worker-type breakdown:")
    for wt, data in sorted(wt_coverage.items()):
        perf = sum(1 for s in data["suites"] if get_suite_harness(s) in ("talos", "raptor"))
        func = sum(1 for s in data["suites"] if get_suite_harness(s) == "functional")
        other = len(data["suites"]) - perf - func
        print(f"    {wt}: {len(data['suites'])} suites ({perf} perf, {func} functional, {other} other)")

    # Suite coverage breadth
    print(f"\n{'=' * 80}")
    print("SUITE COVERAGE BREADTH (narrowest = highest risk)")
    print(f"{'=' * 80}")

    suite_to_workers = defaultdict(set)
    for wt, data in wt_coverage.items():
        for suite in data["suites"]:
            suite_to_workers[suite].add(wt)

    by_breadth = sorted(suite_to_workers.items(), key=lambda x: (len(x[1]), x[0]))

    print(f"\n  === SINGLE WORKER-TYPE (1 point of failure) ===")
    for suite, workers in by_breadth:
        if len(workers) == 1:
            harness = get_suite_harness(suite)
            print(f"  [{harness:10s}] {suite}: {sorted(workers)[0]}")

    print(f"\n  === TWO WORKER-TYPES ===")
    for suite, workers in by_breadth:
        if len(workers) == 2:
            harness = get_suite_harness(suite)
            print(f"  [{harness:10s}] {suite}: {sorted(workers)}")

    print(f"\n  === BROADEST COVERAGE (top 10) ===")
    for suite, workers in list(reversed(by_breadth))[:10]:
        print(f"  {suite}: {len(workers)} worker-types")


def save_json_output(wt_coverage, platform_suites, worker_pools):
    output = {
        "worker_type_coverage": {
            wt: {
                "platforms": data["platforms"],
                "suites": list(data["suites"]),
                "suite_count": len(data["suites"]),
                "platform_count": len(data["platforms"]),
                "perf_suites": [s for s in data["suites"] if get_suite_harness(s) in ("talos", "raptor")],
                "functional_suites": [s for s in data["suites"] if get_suite_harness(s) == "functional"],
            }
            for wt, data in wt_coverage.items()
        },
        "platform_details": {
            name: {
                "suites": suites,
                "os_family": classify_os(name),
            }
            for name, suites in platform_suites.items()
        },
    }

    out_path = BASE / "docs" / "coverage_map.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nJSON output saved to: {out_path}")


if __name__ == "__main__":
    wt_coverage, platform_suites, worker_pools = build_coverage_map()
    print_coverage_report(wt_coverage, platform_suites, worker_pools)
    save_json_output(wt_coverage, platform_suites, worker_pools)
