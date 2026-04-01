"""
Build the suite_matrix.html with actual data injected.
"""

import json
from pathlib import Path

BASE = Path(__file__).parent

with open(BASE / "coverage_map.json") as f:
    cov_data = json.load(f)

wt_data = cov_data["worker_type_coverage"]

# Build data structure
all_wts = sorted(wt_data.keys())
all_suites = set()
for info in wt_data.values():
    all_suites.update(info["suites"])
all_suites = sorted(all_suites)

# Build matrix[suite_idx][wt_idx] = 0 or 1
matrix = []
for suite in all_suites:
    row = []
    for wt in all_wts:
        row.append(1 if suite in wt_data[wt]["suites"] else 0)
    matrix.append(row)

js_data = json.dumps({
    "worker_types": all_wts,
    "suites": all_suites,
    "matrix": matrix,
})

# Read template and inject data
html = (BASE / "suite_matrix.html").read_text(encoding="utf-8")
html = html.replace("MATRIX_DATA_PLACEHOLDER", js_data)

out = BASE / "suite_matrix.html"
out.write_text(html, encoding="utf-8")
print(f"HTML matrix written to: {out}")
print(f"  {len(all_suites)} suites x {len(all_wts)} worker-types")
