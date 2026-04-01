# Session Recap: 2026-03-31

## Goal
Build a test coverage observability dashboard for Firefox CI, starting with static config parsing to understand which test suites run on which OS pools.

## Context Established

### Problem
The team responsible for CI infrastructure images needs visibility into test coverage across OS pools to:
- Safely "green up" new OS pools
- Find tests skipped on all platforms (hidden coverage gaps)
- Avoid losing coverage when decommissioning an OS

### Key GPT-provided context ingested
- Firefox CI is defined in-tree under `taskcluster/`
- `test-sets.yml` groups tests, `test-platforms.yml` binds them to platforms
- No static master list exists — the graph is generated dynamically by Taskgraph
- Tier 1/2 are sheriffed; Tier 3 is informational

---

## Decisions Made

### 1. First deliverable targets
- **Primary**: Pool coverage map (which suites run on which OS pools)
- **Secondary**: Skip matrix (which tests are skipped on which platforms, flag tests skipped everywhere)
- **Deferred**: Pool comparison view (diff two pools)

### 2. Static parsing first, API later
- Parse repo configs first for a quick win
- Treeherder API integration comes later as a second phase

### 3. Two repos to clone (shallow)
- `mozilla-firefox/firefox` — test configs, platform mappings, test manifests
- `mozilla-releng/fxci-config` — pool definitions, worker images

### 4. Alpha pools
- Alpha pools (`-alpha` suffix) are the team's staging/testing ground, currently Windows-only
- Don't filter them out — they indicate greening-up in progress, which is valuable signal
- Only `-alpha` suffix pools are for greening up; don't label non-alpha pools as greening

### 5. Talos naming clarification
- "Talos hardware" = dedicated Linux moonshot machines only (`t-linux-talos-*`)
- "Talos test harness" = the performance test framework (suites named `talos-*`)
- Talos suites run on both Linux (moonshot HW) and Windows, but Windows HW is NUCs (`win11-64-24h2-hw`), not moonshot
- The `windows-talos` test-set in `test-sets.yml` may be stale/orphaned — good catch for cleanup

### 6. Worker-type routing is per-task, not per-platform
- Different suites on the same test platform can route to different worker-types
- Performance suites (talos, browsertime) route to hardware pools
- Functional suites route to VMs
- macOS runs everything on the same physical hardware (no VM/HW split)

### 7. 25h2 vs 24h2 routing
- Test platforms are *named* `windows11-64-24h2-*` in test-platforms.yml
- But `kinds/test/*.yml` override the worker-type to `win11-64-25h2` pools for many suites
- The kinds overrides take precedence over `worker.py` defaults

### 8. Diagram conventions
- Worker-type and test platform are different concepts; don't mix them in one diagram
- Created separate diagrams for each view
- Counts in titles must match what's shown on the y-axis

---

## What We Built

### Parsers
1. **`parse_coverage.py`** — Parses test-platforms.yml, test-sets.yml, and worker.py logic to build a (platform, suite) -> worker-type coverage map. Outputs `coverage_map.json`.
2. **`parse_skips.py`** — Scans 2,711 .toml manifest files for `skip-if` annotations. Outputs `skip_matrix.json`.

### Diagrams
1. **`diagram_worker_types.png`** — Worker-types on y-axis, suite counts as stacked bars (perf/functional/other)
2. **`diagram_test_platforms.png`** — Every test platform on y-axis, suite counts as stacked bars
3. **`diagram_suite_matrix.png`** — Matrix view: suites (rows) x worker-types (columns) with colored dots
4. **`suite_matrix.html`** — Interactive scrollable HTML version of the matrix, with sticky headers, sections (perf/functional/other at top), and risk-colored counts

### Data files
- **`coverage_map.json`** — Full coverage map data (worker-type -> suites, platform details)
- **`skip_matrix.json`** — Skip analysis results

---

## Key Findings

### Coverage map (from parse_coverage.py)
- **20 worker-types** across **64 test platforms** and **135 unique suites**
- **17 suites with single worker-type** (single point of failure)
- `win11-a64-24h2` (ARM64 Windows) only runs 1 suite (`cppunittest`) — very thin
- `win10-64-2009` only has 7 suites — possible decommission candidate
- `windows-talos` test-set may be stale

### Skip matrix (from parse_skips.py)
- **6,091 skip-if entries** across **613 manifest files**
- **548 tests skipped on ALL platforms** — dangerous coverage gaps, no platform runs them
- **238 unconditional skips** (`skip-if = true`)
- Skip counts by OS: Windows 1,809 | Linux 1,688 | Android 1,586 | macOS 1,406
- 1,627 conditions couldn't be mapped to a specific OS (cross-platform conditions like `headless`, `xorigin`)

---

## Open Questions
- What exactly is the difference between a test platform and a worker-type? (pinned for follow-up)
- Is `windows-talos` test-set actually stale or intentional?
- How does the decision task interact with the static config? (context provided but not yet explored)
- Should we account for the `variants.yml` layer (1proc, headless, a11y-checks, etc.)?

---

## Data Sources Identified
- **Firefox repo** `taskcluster/test_configs/` — test-platforms.yml, test-sets.yml, variants.yml
- **Firefox repo** `taskcluster/gecko_taskgraph/transforms/test/worker.py` — worker-type routing logic
- **Firefox repo** `taskcluster/kinds/test/*.yml` — per-suite worker-type overrides
- **fxci-config repo** — worker-pools.yml, worker-images.yml
- **Treeherder API** (treeherder.mozilla.org) — runtime test data (deferred to phase 2)
- **Colleague's dashboard** — https://fqueze.github.io/aretestsfastyet/ (uses Treeherder API, shows skip/flaky rates)

---

## Next Steps
1. Reconcile the 24h2 vs 25h2 worker-type routing discrepancy in the parser
2. Investigate the 548 tests skipped on all platforms — categorize and prioritize
3. Add stale config detection to the parser
4. Begin Treeherder API exploration for phase 2
