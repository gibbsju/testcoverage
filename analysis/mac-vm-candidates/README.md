# macOS VM Migration Candidates

Analysis of which macOS test suites could move from bare metal to Tart VMs on Mac Minis.

## Constraints

- Mac Minis with 16GB RAM
- Tart virtualization, macOS licensing limits to 2 VMs per host
- ~8GB RAM and half CPU cores per VM
- No GPU passthrough in VMs

## Executive summary

143 test suites run on macOS. 87 (61%) are performance suites that must stay on bare metal. Of the remaining 56 functional suites:

**All macOS suites (143):**

| Category | Suites | % of total |
|---|---|---|
| Can move to VM (high confidence) | 23 | 16.1% |
| Can move to VM (pending graphics investigation) | 23 | 16.1% |
| Must stay on bare metal | 95 | 66.4% |
| - Performance suites | 87 | |
| - Functional (heavy/special) | 8 | |

**Tier 1 only (116 must-pass suites):**

| Category | Suites | % of T1 |
|---|---|---|
| Can move to VM (high confidence) | 22 | 19.0% |
| Can move to VM (pending investigation) | 23 | 19.8% |
| Must stay on bare metal | 71 | 61.2% |
| - Performance suites | 66 | |
| - Functional (heavy/special) | 5 | |

**Conservative pitch:** 16% of macOS suites can move to VMs immediately (23 suites).
**Best case:** up to 32% if graphics suites work with SW rendering on macOS VMs (46 suites).

Note: the 16% high-confidence bucket includes the heaviest functional suites (mochitest-plain, mochitest-browser-chrome, web-platform-tests) so the actual compute time freed on bare metal is likely higher than the suite count suggests.

## Functional suites — VM category breakdown

**90% of tier-1 functional suites are potential VM candidates.**

| Category | Tier 1 | % of functional T1 | Action |
|---|---|---|---|
| High confidence VM | 22 | 44% | Ready to pilot |
| Investigate graphics | 23 | 46% | Verify SW rendering on macOS VM |
| Must stay bare metal | 5 | 10% | xpcshell (highcpu), valgrind (memory), geckoview-junit (video), test-coverage-wpt, test-verify-wpt |

## Approach

1. Started with all 143 macOS suites, separated into performance (87) and functional (56)
2. Performance suites (talos, browsertime, awsy) excluded — they need bare metal by definition
3. Checked `virtualization` setting — if a suite is already `virtual` on Linux/Windows, it doesn't need bare metal
4. Flagged suites with GPU/graphics/media keywords for further investigation
5. Flagged suites with `highcpu` instance size or `loopback-video` as resource-heavy
6. Cross-referenced with tier classification (tier 1 = must pass before code lands)

## Important context

- The `virtualization` field in Firefox CI config only branches for Windows (hardware vs virtual). macOS has no VM path today — all tests go to physical Mac worker pools.
- The default `virtualization` is `virtual` — only suites that explicitly set `hardware` (talos) or `virtual-with-gpu` need special treatment.
- Graphics-related suites (reftest, WebGL, WebGPU, etc.) run as `virtual` on Linux/Windows, likely using software rendering. Same approach may work on macOS VMs but needs verification.

## Data

See `analysis.json` for the full categorized data with tier breakdowns.
