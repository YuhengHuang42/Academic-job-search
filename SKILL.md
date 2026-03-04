---
name: academic-job-search
description: Search and shortlist academic jobs with high-recall filtering and two rank buckets (`professor-lecture`, `postdoc-researcher`) across sources. Use when the user asks for academic jobs, postdocs, tenure-track roles, faculty search, or research positions.
homepage: https://github.com/chinpeerapat/jobspy-mcp-server
metadata: {"clawdbot":{"emoji":"🎓","requires":{"bins":["python3"],"env":[]}}}
---

# Academic Job Search

Use this skill to run focused searches for academic roles and return a shortlist with fit reasons.

## Quick start

Run local MCP starter server:

```bash
python3 {baseDir}/scripts/server.py
```

Then call MCP tools:
- `search_academic_jobs`
- `get_supported_academic_sources`
- `get_academic_search_tips`

## Primary sources

Use these as default sources unless user asks otherwise:
- `academicjobsonline` for global faculty/postdoc listings and deadlines
- `academicwork` for Canadian higher-ed listings (CAUT board)
- `cra` for computing research/faculty opportunities from the CRA career center
- `jobsacuk` for UK and international higher-ed opportunities from jobs.ac.uk
- `jrecin` for Japan-focused academic and research roles
- `linkedin` for broader academic, research, and institute postings

## When to use

Use this workflow when user requests:
- Academic jobs
- Postdoc positions
- Faculty or tenure-track search
- Lecturer or research scientist roles
- University or institute hiring

## Workflow

1. Clarify hard constraints first:
   - Field/subfield (for example: "CS > ML", "Biology > Genomics")
   - Target rank (`professor-lecture` or `postdoc-researcher`)
   - Location and remote preference
   - Visa sponsorship requirement
   - Deadline window

2. Run a small first pass search (10-20 results) via MCP tool:

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

3. Evaluate results and explain ranking:
   - Query relevance
   - Rank/field alignment
   - Deadline urgency
   - Hard-constraint match

4. Refine with one or two targeted changes:
   - Broaden or narrow field taxonomy
   - Add/remove sources
   - Adjust deadline window or geography

5. Return final shortlist with:
   - Why each role fits
   - Missing critical information
   - Next query suggestions

## Output format

Return results in this structure:

```markdown
## Top Matches
- <Job Title> at <Institution> (<Location>)
  - Fit: <1-2 concise reasons>
  - Deadline: <date or unknown>
  - Visa: <supported/unknown/not listed>
  - Link: <url>

## Gaps to verify
- <missing detail 1>
- <missing detail 2>

## Next search iteration
- <query tweak 1>
- <query tweak 2>
```

## Source quality rules

- Prefer official institution postings over reposts.
- De-duplicate by normalized `(institution, title, location, deadline)`.
- If deadline is missing, flag as "verify".
- If visa info is missing, do not assume sponsorship.
- For `jrecin`, support JP/EN text and keep original Japanese title when available.
- For `linkedin`, mark role as "aggregator" unless an official institution URL is present.

## Safe defaults

- Start with `max-results` 15.
- Default sources: `academicjobsonline`, `academicwork`, `cra`, `jobsacuk`, `jrecin`, `linkedin`.
- `search_term` is a soft preference for scoring, not a hard filter.
- Do not over-constrain keyword matching; keep recall high and let downstream reasoning shortlist.
- If `location` is Japan, prioritize `jrecin`; otherwise prioritize `academicjobsonline` + `linkedin`.

## Notes

- Be transparent about uncertainty (deadline/visa/salary often missing).
- Prioritize deadlines and fit over raw volume.
- If user has no constraints, ask for field + rank bucket + region before searching.
