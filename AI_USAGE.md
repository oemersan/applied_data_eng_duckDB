# AI Usage Disclosure

This file documents how AI tools were used in preparing this submission, as
required by the YZV 322E individual tool presentation assignment guidelines.

## Tool used

**Claude (Anthropic)** — used as a coding and writing assistant via the chat
interface during the preparation phase (April 2026).

## What it was used for

| Task | AI involvement | Human review |
|---|---|---|
| Selecting the dataset (NYC Yellow Taxi Parquet) | Suggested the dataset and rationale | I confirmed it was a good fit and verified the URL |
| Repository structure | Suggested the layout (scripts/, notebooks/, etc.) | I adopted it as proposed |
| `docker-compose.yml` | Drafted the Postgres + pgAdmin services | I reviewed the env-var defaults and the healthcheck |
| `scripts/01..04_*.py` | Drafted the benchmark scripts | I read each line, ran them locally, and verified the timing output matched the README |
| `README.md` | Drafted the structure and prose | I edited the prerequisites table and troubleshooting section to match what I actually hit on my machine |
| Slide deck text | Bullet-point suggestions for each slide | I rewrote in my own words, edited for the 10-15 min timing |
| Verifying facts (release year, license, current version) | Looked up DuckDB v1.5.2 release date and creators on duckdb.org and Wikipedia | I cross-checked the citations |

## What it was NOT used for

- **No unreviewed AI output was submitted.** Every script was run on my own
  machine before being committed. Every claim in the README about timings
  is from my own runs, not AI-imagined numbers.
- The video recording, narration, and any spoken explanation in the
  presentation are mine. AI was not used to generate audio or video.
- The choice of tool (DuckDB) and the framing of the comparison
  (vs Pandas, vs Postgres) are mine.

## Why I disclose this

The assignment explicitly requires AI usage disclosure and warns that
submitting unreviewed AI output is not acceptable. I agree with that
position: AI is useful as a sparring partner for structure and boilerplate,
but the engineering judgment, the running code, and the spoken presentation
have to be mine.
