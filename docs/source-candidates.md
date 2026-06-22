# Academic Job Source Candidates

This note records additional sources worth considering for the academic job search MCP.

## Highest-Priority Additions

- `linkedin`: Priority discovery source. The current repo lists LinkedIn but its connector returns no rows; it needs an approved API, export workflow, or compliant provider. Use LinkedIn leads to discover postings, then prefer official institution/application URLs for canonical records.
- `acm`: ACM Career & Job Center. Strong fit for Computer Science, AI, software engineering, systems, faculty, postdoc, and research roles.
- `euraxess`: European Commission EURAXESS Jobs & Opportunities. Strong fit for European postdoc/researcher roles and some faculty-style academic posts.
- `higheredjobs`: Broad North American higher-education job board. Strong fit for assistant/associate professor roles, with a need for careful filtering.
- `academicpositions`: European/global academic job board with useful filtering by field and position type. Strong fit for assistant/associate professor, postdoc, and researcher roles in CS/AI/software/systems.
- `academictransfer`: Netherlands-focused academic and research jobs. Strong fit for postdoc, researcher, assistant professor, and associate professor roles.
- `interfolio`: Important application/job infrastructure for faculty, postdoc, fellowship, and grant opportunities. Useful as a discovery source if a compliant listing endpoint is available.

## Medium-Priority Additions

- `ieee`: IEEE Job Site. Useful for computing, engineering, AI, systems, robotics, and ECE-adjacent academic/research roles.
- `academic-keys`: Higher-ed job board with discipline-focused sites and faculty/postdoc coverage.
- `nature-careers`: Global science jobs board. Useful for research scientist and postdoc roles; lower precision for CS faculty than ACM/CRA.
- `science-careers`: AAAS Science Careers. Useful for scientific postdoc/researcher roles; lower precision for CS faculty than ACM/CRA.
- `hpcwire`: Useful for systems/HPC/research-computing roles, but not primarily a professor/postdoc board.

## Community/Tracking Sources

- `academic-jobs-wiki`: Useful for faculty-search tracking and status intelligence, but community-edited and less suitable as a canonical source of posting truth.

## Institutional Watchlist Sources

- `tuwien-informatics`: TU Wien Informatics jobs/news pages. This should catch roles such as Assistant Professor of Software Engineering that are published on faculty news and institutional job pages before, or instead of, appearing on broad boards.
- `tuwien-jobs`: TU Wien central job platform. Useful for canonical application links, deadlines, salary, and materials.

## Implementation Notes

- Prefer official university/institute URLs after discovery from any aggregator.
- Treat LinkedIn as a priority discovery layer, not just another board. If a LinkedIn result points to an official application page, ingest the official URL and deduplicate against institutional connectors.
- Keep `search_term` soft and use field/rank/title scoring to preserve recall.
- Offer a broad discovery pass as an optional recall audit rather than running it every time. When requested, start with terms such as `computer science`, `computing`, `informatics`, `computer engineering`, and `information science`; inspect top returned titles/institutions for relevant roles missing from focused AI/SE/systems queries; then fold recurring useful terms back into the profile.
- In the first broad CS smoke test, useful missing vocabulary included `computing`, `computing science`, `data science`, `cybersecurity`, and `cyber security`. Broad postdoc searches also produced unrelated physics/chemistry results from general boards, so broad-pass results should be reviewed for an actual CS/computing signal before being promoted.
- The TU Wien Assistant Professor of Software Engineering miss was a source-coverage failure, not a keyword failure. It matched the profile well but lived on institutional pages outside the implemented connectors, so add institutional watchlist/feed connectors for priority departments.
- For the CS profile, boost source/query combinations that mention AI, machine learning, software engineering, computer systems, distributed systems, operating systems, and research scientist/postdoc language.
- For each new connector, document terms/robots behavior before enabling live fetches.
