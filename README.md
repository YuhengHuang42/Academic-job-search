# Academic Job Search MCP

FastMCP server for academic job search across multiple public and configured sources.

## Sources

The current source connectors are:

- `academicjobsonline`
- `academicwork`
- `cra`
- `jobsacuk`
- `jrecin`
- `linkedin`

AcademicJobsOnline, AcademicWork, CRA, jobs.ac.uk, and JREC-IN fetch public listing pages. The LinkedIn connector is a compliant placeholder and returns no rows until an approved provider, API, or export workflow is configured.

Additional source candidates and implementation notes are tracked in `docs/source-candidates.md`.

## Project Status

This project is intentionally simple:
- Tools are implemented and runnable.
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

## Contributing

Pull requests of any kind are welcome: new sources, parser fixes, docs, tests, cleanup, better scoring, compliance notes, and small usability improvements all help.

## Next steps

1. Replace mock connector outputs in `scripts/connectors/*.py` with real fetch/parse logic.
2. Keep each connector output in the normalized record shape used by `server.py`.
3. Add request pacing and terms/robots compliance per source.
