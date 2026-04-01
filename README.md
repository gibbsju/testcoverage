# Firefox CI Test Coverage Observatory

Research platform to map test suite coverage across Firefox CI worker pools and identify coverage gaps. This is a discovery project — findings here will inform requirements for a production dashboard in a separate repo.

## Site

The `docs/` folder is served via GitHub Pages:

- **Landing page** — overview stats and diagram gallery
- **Suite coverage matrix** — which suites run on which worker-types (interactive)
- **Test-level skip matrix** — individual tests with skip-if conditions by OS (filterable)

## Structure

```
docs/       -- GitHub Pages site (the deliverable)
scripts/    -- Python parsers that generated the data
history/    -- Session recaps and research notes
```

## Regenerating

Requires Python 3.10+, PyYAML, matplotlib, and shallow clones of the Firefox and fxci-config repos.

```bash
pip install pyyaml matplotlib
git clone --depth 1 <firefox-repo-url> ./firefox
git clone --depth 1 <fxci-config-repo-url> ./fxci-config
python scripts/parse_coverage.py
python scripts/parse_skips.py
python scripts/build_matrix_html.py
python scripts/build_test_skip_html.py
python scripts/generate_diagrams.py
```
