# Firefox CI: Suite x Worker-Type Matrix

Generated: 2026-03-31 | 135 suites x 20 worker-types

Legend: `*` = suite runs on this worker-type | `#` = total worker-types running this suite

| OS | Linux|Linux|Linux|Linux|Linux|Linux|Linux|Windows|Windows|Windows|Windows|Windows|Windows|macOS|macOS|macOS|Android|Android|Android|Android | |
| Suite | linux-docker | linux-kvm | linux-netperf-1804 | linux-netperf-2404 | linux-talos-1804 | linux-talos-2404 | linux-wayland | win10-64-2009 | win11-64-24h2 | win11-64-24h2-gpu | win11-64-24h2-hw | win11-64-24h2-hw-ref | win11-a64-24h2 | osx-1015-r8 | osx-1400-r8 | osx-1500-m4 | bitbar-p5 | bitbar-p6 | bitbar-s24 | lambda-a55 | # |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| **--- Performance (77 suites) ---** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | |
| browsertime-benchmark-jetstream2 |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-benchmark-jetstream3 |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-benchmark-motionmark-1-3 |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-benchmark-unity-webgl-mobile |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-tp6m |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-tp6m-essential |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-tp6m-live |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-tp6m-webextensions |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-trr-performance-m |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-video-playback-latency-mobile |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| browsertime-youtube-playback-mobile |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| talos-xperf |   |   |   |   |   |   |   |   | `*` |   |   |   |   |   |   |   |   |   |   |   | **1** |
| talos-g3 |   |   |   |   | `*` | `*` |   |   |   |   |   |   |   |   |   |   |   |   |   |   | 2 |
| browsertime-benchmark-speedometer2-mobile |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | `*` | `*` | 3 |
| browsertime-benchmark-speedometer3-mobile |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | `*` | `*` | 3 |
| browsertime-tp6-profiling |   |   |   |   | `*` | `*` |   |   |   |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| browsertime-youtube-playback-power-mobile |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | `*` | `*` | 3 |
| browsertime-benchmark-wasm |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-custom |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-first-install |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-indexeddb |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-network-bench |   |   | `*` | `*` |   |   |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-pageload-benchmark |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-regression-tests |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-responsiveness |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-speculative |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-throttled |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-tp6 |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-tp6-bytecode |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-tp6-essential |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-tp6-live |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-tp6-live-sheriffed |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-tp6-webextensions |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-tp7 |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-trr-performance |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-upload |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-webcodecs |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-youtube-playback |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-youtube-playback-power |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-bcv |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-bcv-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-chrome |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-chrome-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-damp-inspector |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-damp-other |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-damp-webconsole |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-dromaeojs |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-dromaeojs-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-g1 |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-g1-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-g3-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-g4 |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-g4-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-g5 |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-g5-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-motionmark-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-other |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-other-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-pdfpaint |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-perf-reftest |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-perf-reftest-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-perf-reftest-singletons |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-perf-reftest-singletons-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-realworld-webextensions |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-realworld-webextensions-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-sessionrestore-many-windows |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-sessionrestore-many-windows-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-svgr |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-svgr-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-tabswitch |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-tabswitch-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-tp5o |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-tp5o-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-webgl |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| talos-webgl-profiling |   |   |   |   | `*` | `*` |   |   |   |   | `*` |   |   |   | `*` |   |   |   |   |   | 4 |
| browsertime-video-playback-latency |   |   |   |   | `*` | `*` |   |   |   |   | `*` | `*` |   |   | `*` |   |   |   |   |   | 5 |
| browsertime-benchmark |   |   |   |   | `*` | `*` |   |   |   |   | `*` | `*` |   |   | `*` | `*` |   |   |   |   | 6 |
| **--- Functional (53 suites) ---** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | |
| crashtest-qr |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| geckoview-junit |   | `*` |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | **1** |
| jittest-all |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` |   |   |   | **1** |
| mochitest-browser-chrome-failures |   |   |   |   |   |   | `*` |   |   |   |   |   |   |   |   |   |   |   |   |   | **1** |
| reftest-qr |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | `*` | **1** |
| mochitest-browser-screenshots | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   |   |   |   |   |   |   | 2 |
| test-coverage | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   |   |   |   |   |   |   | 2 |
| test-coverage-wpt | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   |   |   |   |   |   |   | 2 |
| mochitest-webgpu | `*` |   |   |   |   |   |   |   |   | `*` |   |   |   |   | `*` |   |   |   |   |   | 3 |
| web-platform-tests-webgpu | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| web-platform-tests-webgpu-backlog | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| web-platform-tests-webgpu-backlog-long | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| web-platform-tests-webgpu-long | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| web-platform-tests-backlog | `*` | `*` |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 4 |
| web-platform-tests-reftest-backlog | `*` | `*` |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 4 |
| firefox-ui-functional | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| jsreftest | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| marionette-integration | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| marionette-unittest | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| mochitest-a11y | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| mochitest-browser-a11y | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| mochitest-browser-chrome | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   | 5 |
| mochitest-browser-media | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| mochitest-browser-translations | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| mochitest-devtools-chrome | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| mochitest-remote | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| telemetry-tests-client | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| test-verify-gpu | `*` |   |   |   |   |   | `*` |   |   | `*` |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| test-verify-wpt | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| web-platform-tests-canvas | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| web-platform-tests-print-reftest | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 5 |
| mochitest-chrome | `*` |   |   |   |   |   | `*` | `*` | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| mochitest-chrome-gpu | `*` |   |   |   |   |   | `*` | `*` | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| mochitest-webgl2-ext | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   |   | 6 |
| reftest | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| test-verify | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| web-platform-tests | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| web-platform-tests-crashtest | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| web-platform-tests-eme | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| web-platform-tests-reftest | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| web-platform-tests-wdspec | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| web-platform-tests-webcodecs | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 6 |
| crashtest | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   |   | 7 |
| gtest | `*` | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 7 |
| jittest | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   | `*` | `*` | `*` | `*` |   |   | `*` | 7 |
| mochitest-plain | `*` | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 7 |
| mochitest-plain-gpu | `*` | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   |   |   | `*` | `*` |   |   |   |   | 7 |
| mochitest-webgl1-core | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   | `*` | 7 |
| mochitest-webgl1-ext | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   | `*` | 7 |
| mochitest-webgl2-core | `*` |   |   |   |   |   | `*` |   | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   | `*` | 7 |
| xpcshell | `*` | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   |   | 8 |
| cppunittest | `*` | `*` |   |   |   |   | `*` | `*` | `*` |   |   |   | `*` | `*` | `*` | `*` |   |   |   |   | 9 |
| mochitest-media | `*` | `*` |   |   |   |   | `*` |   | `*` |   |   | `*` |   | `*` | `*` | `*` |   |   |   | `*` | 9 |
| **--- Other / AWSY (5 suites) ---** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | |
| awsy | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| awsy-base | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| awsy-base-dmd | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| awsy-dmd | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |
| awsy-tp6 | `*` |   |   |   |   |   |   |   | `*` |   |   |   |   |   | `*` |   |   |   |   |   | 3 |