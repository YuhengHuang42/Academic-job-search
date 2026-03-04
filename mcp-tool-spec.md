# Academic Job MCP Tool Spec (Minimal)

This spec defines a minimal MCP surface for fit-aware academic job search.

## Tool 1: `search_academic_jobs`

Search across configured academic job sources and return normalized results.

Default sources for v1:
- `academicjobsonline`
- `academicwork`
- `cra`
- `jobsacuk`
- `jrecin`
- `linkedin`

### Input schema

```json
{
  "search_term": "string (required)",
  "field": "string (optional, taxonomy path like computer-science/ml)",
  "rank": "string (optional: professor-lecture|postdoc-researcher; aliases accepted)",
  "location": "string (optional)",
  "country": "string (optional, ISO-2 preferred)",
  "is_remote": "boolean (optional, default false)",
  "visa_needed": "boolean (optional)",
  "deadline_before": "string (optional, YYYY-MM-DD)",
  "posted_within_days": "number (optional)",
  "sources": "string[] (optional; values: academicjobsonline|academicwork|cra|jobsacuk|jrecin|linkedin)",
  "language_hint": "string (optional; auto|en|ja, default auto)",
  "max_results": "number (optional, default 15, max 200)",
  "offset": "number (optional, default 0)",
  "verbose": "number (optional, 0-2, default 1)"
}
```

### Output schema

```json
{
  "query": {
    "search_term": "string",
    "field": "string|null",
    "rank": "string|null"
  },
  "results": [
    {
      "id": "string",
      "title": "string",
      "institution": "string",
      "department": "string|null",
      "location": "string|null",
      "country": "string|null",
      "rank": "string|null",
      "field_tags": ["string"],
      "employment_type": "string|null",
      "posted_date": "string|null",
      "deadline": "string|null",
      "visa_info": "string|null",
      "salary_range": "string|null",
      "requirements": ["string"],
      "materials": ["string"],
      "url": "string",
      "source": "string",
      "source_type": "string (official-board|aggregator)",
      "language": "string (en|ja|other|null)",
      "fit_score": "number (0-100)",
      "fit_reasons": ["string"]
    }
  ],
  "meta": {
    "total_found": "number",
    "returned": "number",
    "deduplicated": "number",
    "sources_used": ["string"],
    "warnings": ["string"]
  }
}
```

### Ranking baseline

- 40% query relevance
- 25% rank + field alignment
- 20% deadline urgency/recency
- 15% hard constraints (location/visa/remote)

Matching behavior:
- `search_term` is a soft preference (ranking signal), not a hard filter.
- Rank is a hard filter when provided.

Return `fit_reasons` to make ranking explainable.

### Source-specific behavior

- `academicjobsonline`: treat as high-signal official-board feed with strong deadline signal.
- `academicwork`: treat as official-board source with strong Canadian higher-ed coverage.
- `cra`: treat as a society-operated board with strong computing-research relevance.
- `jobsacuk`: treat as a high-coverage UK-centric academic board with international listings.
- `jrecin`: support Japanese taxonomy and JP/EN mixed text; map domestic rank labels to canonical rank values.
- `linkedin`: treat as aggregator by default; boost only when official institution posting is verified.

Regional fallback:
- If `location` or `country` implies Japan, apply a mild source prior for `jrecin`.
- Otherwise prioritize `academicjobsonline` + verified institution postings from `linkedin`.

## Tool 2: `get_supported_academic_sources`

Returns available sources and notes on reliability/rate limits.

### Output

```json
{
  "sources": [
    {
      "name": "string",
      "category": "official-board|aggregator|society|institution",
      "regions": ["string"],
      "languages": ["string"],
      "notes": "string"
    }
  ]
}
```

## Tool 3: `get_academic_search_tips`

Returns concise search guidance and parameter examples.

### Output

```json
{
  "tips": ["string"],
  "examples": [
    {
      "label": "string",
      "query": {}
    }
  ]
}
```

## Error model

All tools should return structured errors:

```json
{
  "error": {
    "code": "INVALID_ARGUMENT|RATE_LIMITED|SOURCE_UNAVAILABLE|INTERNAL",
    "message": "string",
    "retryable": "boolean"
  }
}
```

## Implementation notes

- Canonical rank buckets are `professor-lecture` and `postdoc-researcher`.
- Normalize rank aliases (`assistant professor`, `asst prof`, `associate professor`, `lecturer`, `postdoc`, `research scientist`) to canonical values.
- Add JP rank alias mapping for `jrecin` labels (for example `教授相当`, `准教授相当`, `助教相当`, `研究員・ポスドク相当`).
- Keep raw source payload internally for debugging but return normalized fields to clients.
- Deduplicate before ranking.
- Do not infer visa sponsorship unless explicitly present in source text.
- Respect each source terms and robots rules for collection and request frequency.
