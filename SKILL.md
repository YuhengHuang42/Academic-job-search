---
name: academic-job-search
description: Search, diagnose, and shortlist academic jobs with high-recall filtering across faculty, lecturer, postdoc, researcher, and research-scientist roles. Use when the user asks for academic jobs, postdocs, tenure-track roles, faculty searches, lecturer searches, or university/institute research positions.
homepage: https://github.com/chinpeerapat/jobspy-mcp-server
metadata: {"clawdbot":{"emoji":"🎓","requires":{"bins":["python3"],"env":[]}}}
---

# Academic Job Search

Use this skill to run focused academic job searches, preserve recall, explain fit, and surface gaps that need human verification.

## Available Tools

Run the local MCP server when needed:

```bash
python3 {baseDir}/scripts/server.py
```

Primary MCP tools:

- `search_academic_jobs`
- `get_supported_academic_sources`
- `get_academic_search_tips`

## Default Sources

Use all configured sources unless the user asks for a narrower scope:

- `academicjobsonline`: global faculty/postdoc board with strong deadline signal.
- `academicwork`: Canadian higher-ed listings from AcademicWork/CAUT.
- `cra`: computing research and faculty opportunities from the CRA Career Center.
- `jobsacuk`: UK-centric academic board with many international higher-ed roles.
- `jrecin`: Japan-focused academic and research roles, including JP/EN mixed listings.
- `linkedin`: discovery source only until a compliant provider/API/export workflow is configured; prefer official institution URLs when found.

Additional source candidates and watchlists live in `docs/source-candidates.md`.

## Operating Principles

- Keep recall high on the first pass. Treat `search_term` as a ranking signal, not a hard filter.
- Treat rank as a hard filter only when the user explicitly gives one of the canonical buckets.
- Prefer official institution or official-board postings over reposts and aggregators.
- Never infer visa sponsorship, salary, or deadline from context. If missing, mark it `unknown` or `verify`.
- Deduplicate before ranking, normally by normalized institution, title, location, deadline, and URL when available.
- Explain ranking with short fit reasons tied to field, rank, location, deadline, or source reliability.
- Respect each source's terms, robots rules, and request pacing before enabling live fetches.

## Canonical Buckets

Use these rank buckets in queries and explanations:

- `professor-lecture`: assistant/associate/full professor, lecturer, senior lecturer, teaching professor, faculty position.
- `postdoc-researcher`: postdoc, research fellow, research associate, research scientist, staff scientist, institute researcher.

For JREC-IN, map Japanese rank labels such as `教授相当`, `准教授相当`, `助教相当`, and `研究員・ポスドク相当` into the closest canonical bucket while keeping the original title.

## Workflow

1. Identify hard constraints:
   - field/subfield, such as `computer-science/ml`
   - rank bucket, if the user cares
   - country/region, remote preference, and visa needs
   - deadline window or urgency

2. Run a small high-recall first pass:

```bash
search_academic_jobs \
  --search-term "machine learning" \
  --field "computer-science/ml" \
  --rank "postdoc-researcher" \
  --location "usa" \
  --sources "academicjobsonline,academicwork,cra,jobsacuk,jrecin,linkedin" \
  --visa-needed true \
  --max-results 20
```

3. Inspect the returned meta and warnings:
   - If a source returns zero rows, mention it as a diagnostic rather than treating it as proof that no jobs exist.
   - If `linkedin` returns zero rows, say that it needs a compliant provider/API/export workflow.
   - If live network access failed, rerun with approved network access before interpreting the result set.
   - If one source dominates the volume, still check whether smaller high-signal sources surfaced good matches.

4. Shortlist and refine:
   - Promote listings with explicit field and rank alignment.
   - Downrank broad science results that only match a rank bucket but lack field signal.
   - Use one or two follow-up queries to cover missing vocabulary or regions.
   - For broad CS discovery, include variants such as `computing`, `computing science`, `data science`, `cybersecurity`, `cyber security`, `software engineering`, `distributed systems`, `HPC`, and `computer systems`.

5. Return a concise shortlist plus gaps and next steps.

## Regional And Source Guidance

- Japan: prioritize `jrecin`; preserve Japanese titles; support Japanese and English text.
- UK/Ireland: use `jobsacuk` heavily, then verify official institution pages for top matches.
- Canada: include `academicwork` for higher-ed coverage.
- Computing/CS: include `cra`, `academicjobsonline`, `jobsacuk`, and any relevant institutional watchlist.
- Institutional misses are source-coverage failures, not keyword failures. If a known department or university matters, search or add its official jobs page.

## Output Format

Use this shape unless the user asks for something else:

```markdown
## Top Matches
- <Job Title> at <Institution> (<Location>)
  - Fit: <1-2 concise reasons>
  - Deadline: <date or unknown>
  - Visa: <supported/unknown/not listed>
  - Link: <url>

## Gaps To Verify
- <missing detail 1>
- <missing detail 2>

## Source Diagnostics
- <source behavior, warnings, or notable omissions>

## Next Search Iteration
- <query tweak 1>
- <query tweak 2>
```

## Safe Defaults

- Start with `max_results` 15-20.
- Default sources: `academicjobsonline`, `academicwork`, `cra`, `jobsacuk`, `jrecin`, `linkedin`.
- If the user has no constraints, ask for field, rank bucket, and region before running a broad search.
- Prioritize deadline urgency and genuine fit over raw volume.
- Be transparent when detail pages still need manual verification.
