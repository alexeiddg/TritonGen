# Preliminary report — `docs/preliminary_report/`

Single-file HTML report on the 2² factorial subset over grammar guidance (G) and correctness feedback (C). Intended for the in-person preliminary meeting; recipients open the file in a browser, no Python or local server required.

## Files

| File | Purpose |
|---|---|
| `index.html` | The report (English). Self-contained except for one CDN script (Chart.js 4.4). Embedded JSON data, ~43 KB total. |
| `index.es.html` | Spanish variant. Same structure, same embedded data, prose translated. Cross-linked with the English version via a language switch in the header. |
| `_build_data.py` | Generates `_report_data.json` from the analyzer JSON and raw JSONL artifacts. |
| `_report_data.json` | Aggregated data emitted by `_build_data.py`. Already inlined into both HTML files; this file is regeneration evidence, not loaded at runtime. |

## How to open

```bash
open docs/preliminary_report/index.html         # macOS, English
open docs/preliminary_report/index.es.html      # macOS, Spanish
xdg-open docs/preliminary_report/index.html     # Linux
```

Or double-click the file. Both versions cross-link via a small language switch in the top-right of the header. Requires internet access for the Chart.js CDN to load; charts will not render offline. If offline rendering is needed, download `chart.umd.min.js` from jsdelivr and swap the `<script src="...">` for a local path.

## Sources

The report cites and aggregates from:

- `outputs/analysis/factorial_2x2_preliminary.json` — primary authority for condition rates, Wilson CIs, paired comparisons, factorial-model status, and F3 policy.
- `outputs/cluster1/baseline_repaired_l4_n20.jsonl` — *none* (180 rows).
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` — *G* (177 rows).
- `outputs/cluster2/c_paper_n20_l4.jsonl` — *C* (180 rows).
- `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` — *G+C* (177 rows).
- `outputs/cluster1/final_g_l4_n20.jsonl` — Template-G reference upper bound (180 rows), shown for comparison only; not part of the factorial.

Methodology prose is anchored in `docs/02_methodology_cluster1.md`, `docs/03_methodology_cluster2.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `docs/07_analysis_and_statistics.md`, and `docs/08_decision_log.md`.

## Regenerating after the data changes

If any source artifact or the analyzer JSON is updated:

```bash
python3 docs/preliminary_report/_build_data.py
```

This rewrites `_report_data.json`. Then re-inline it into the HTML — the report parses the JSON from a `<script id="report-data">` block near the bottom of `index.html`:

```bash
python3 - <<'PY'
import json, pathlib
html = pathlib.Path('docs/preliminary_report/index.html').read_text()
data = pathlib.Path('docs/preliminary_report/_report_data.json').read_text().strip()
compact = json.dumps(json.loads(data), separators=(',', ':'))

# Replace the existing JSON between the script tags.
import re
new = re.sub(
    r'(<script id="report-data" type="application/json">\s*)(.*?)(\s*</script>)',
    lambda m: m.group(1) + compact + m.group(3),
    html, count=1, flags=re.DOTALL,
)
pathlib.Path('docs/preliminary_report/index.html').write_text(new)
PY
```

Prose (headline sentence, four-question answers, headline-numbers table, paired-comparison table, methodology and threats sections) is hand-written and lives in `index.html` and `index.es.html`. If the underlying numbers shift materially, those passages need a manual edit in **both** language variants — they cite specific values like `3 / 177` and `1.69%`. The two files share the same data, CSS, and chart JS; only the human-facing strings differ.

## Caveats baked into the report

- The analyzer now marks `metadata.reportable=true` under explicit `analysis_cli_annotation`; the report remains preliminary and must preserve coverage, F3, P-deferred, model-fit, and provenance caveats.
- *None* and *G* are Cluster 1 (compile-only); functional success is normalized to false/unproven, not measured at Level 2.
- G and G+C have 177/180 coverage after 3 matmul rows were lost to Modal payload failures (policy: `COVERAGE_WARNING_SKIP_MISSING`).
- G+C compile-rate denominator is 172 after F3_EVAL_PIPELINE exclusion (5 rows); matched-pair analysis uses n=177.
- The full 2³ factorial over G, C, and P is the project goal. The P factor (Cluster 3) is deferred to the June 4–7 implementation window.
