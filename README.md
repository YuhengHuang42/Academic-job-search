# Academic Job Search MCP (Starter)

Minimal FastMCP starter for academic job search across:
- `academicjobsonline`
- `academicwork`
- `cra`
- `jrecin`
- `linkedin`

This starter is intentionally simple:
- Tools are implemented and runnable.
- AcademicJobsOnline and JREC-IN connectors fetch public listing pages.
- LinkedIn connector is a compliant placeholder (returns no rows until provider/API is configured).
- Normalization, deduplication, and fit scoring are included.
- Rank is normalized to two buckets: `professor-lecture` and `postdoc-researcher`.
- `search_term` is treated as a soft relevance signal to keep recall high.

## Prerequisites

- Python 3.10+
- `mcp` package with FastMCP support

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "mcp>=1.1.0"
```

## Run

```bash
python3 {baseDir}/scripts/server.py
```

## Next steps

1. Replace mock connector outputs in `scripts/connectors/*.py` with real fetch/parse logic.
2. Keep each connector output in the normalized record shape used by `server.py`.
3. Add request pacing and terms/robots compliance per source.
