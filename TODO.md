# TODO

## Phase 2 Grading — Carryovers from the Apr 26 build session

These were either spawned as chips in that session (some chips may have been dismissed) or noted as scope cuts. Treat this list as the canonical backlog for grading-related follow-ups; the Phase 2 plan (`plans/phase2/`) is feature-complete except for these.

### Modeling / data quality

- [ ] **Add tests for appearance ingest + new player fields.** Task 1 added a 180-line `pipeline/ingest_appearances.py` and seven new `Player` columns without unit-test coverage. Cover: upsert idempotency, missing-player/club skip paths, NaN-stats coercion, `_normalize_foot` edge cases, `_market_value_to_cents` overflow, `_parse_date` ISO vs US formats, intra-CSV duplicate handling.

- [ ] **Make appearances `competition_id` schema-optional.** Currently in `REQUIRED_COLUMNS` (`api/pipeline/ingest.py` lines 127-131); a Transfermarkt rename would abort the whole pipeline even though the column is nullable in our schema and only consumed by Task 3's minutes-pct denominator (which already filters NULL competitions). Move to KNOWN-only.

- [ ] **Phase 3: FM attribute ingestion + ML model for the cases the heuristic floor can't reach.** The v0.1.0 release ships with a `tenure_success_floor` heuristic that lifts long-tenure high-minutes stints (Alisson F → B, Rodri C+ → B+, De Bruyne C+ → B+, etc.). It's a stopgap. The remaining curated misses (Alisson 77.5, Álvarez 77.2 — both ~0.5–0.8 below B+) and the structural gap with Kanté (G+A is a poor proxy for DM contribution) need attribute-level data. Phase 3 adds: (a) Football Manager attribute ingestion for tackles/interceptions/positioning/leadership, (b) a gradient-boosted tree trained on those + the existing component scores, swapped in via the `phase3_ml_model_path` hook in `scoring_config.json`. See `GRADING_NOTES.md` final iteration log for the full breakdown.

- [ ] **Promote shared CSV ingest helpers to a public module.** `pipeline/ingest_appearances.py` imports six leading-underscore names (`_validate_schema`, `_safe_str`, `_safe_int_str`, `_coerce_int_default`, `_parse_date`) from `pipeline.ingest` — violates Python convention. Either drop the underscores or move to `pipeline/csv_utils.py`.

- [ ] **Verify the upsert helper's SQLite fallback covers all call sites.** `pipeline/upsert.py` has a Postgres-only fast path and a SQLite query-then-upsert fallback for tests. The fallback is exercised by `TestIngestValuations`, `TestIngestTransfers`, and the E2E pipeline tests under SQLite, but not formally documented as a "test-only path." If a future call site needs production-grade upsert semantics under SQLite, the fallback contract may need extending.

### Validation / completeness

- [ ] **Re-run validation after any tuning, append findings to `GRADING_NOTES.md`** rather than overwriting. `just validate` produces the text-only summary; `just validate-png` also drops a histogram at `api/models/grade_distribution.png`. The notes file is intentionally a chronological log so we can see how the distribution shifts as we tune.

## API Optimizations

- [ ] **Collapse duplicate queries in club network endpoint** — `GET /clubs/{id}/network` in `api/app/services/club_service.py` runs two separate DB queries (bought_query + sold_query) that scan the same transfers table and merge results in Python. Can be consolidated into a single query with CASE expressions, same pattern we applied to the country detail endpoint. Low priority — response times are already <10ms.

## Detail Panel

- [ ] **Fee filter chip resizes when switching Buying/Selling/Both** — In the filter bar, the Fee chip summary text changes width when the direction toggle changes the data (different fee ranges appear). The chip should maintain a fixed width regardless of the displayed value.

## Network Graph

- [ ] **Pipeline doesn't flag loan returns as loans** — In `api/pipeline/parse.py`, loan returns (player going back to parent club after loan) show as `fee=0, fee_is_loan=false` instead of `fee_is_loan=true`. The `parse_fee()` function only detects loans from the fee string ("loan transfer", "Loan fee:"), but loan returns that show as `fee=0` with no "loan" keyword get classified as free transfers. Needs additional heuristics — e.g. if a player returns to a club they previously left within 1-2 seasons, flag it as a loan return.

## Player Page

- [ ] **Add country flags to career timeline** — The career timeline in `web/src/components/organisms/CareerTimeline.tsx` currently shows club initials in placeholder boxes. Replace with country flag emojis for each club's country. The club's `country_id` isn't currently in the transfer data returned by `GET /players/{id}` — would need to add it to the API response, then use `getFlag()` from `lib/flags.ts`.

- [ ] **Club logos in career timeline** — Find a properly licensed source for club crest images. Options: (1) a Creative Commons dataset, (2) an API with explicit open-source usage terms. Transfermarkt CDN hotlinking and football-data.org crests both have unclear licensing. Until resolved, the initials fallback works fine.

## Network Graph

- [ ] **Graph doesn't fully re-fit when sidebar opens/closes** — When clicking a country or club node on the network graph, the detail sidebar opens and the graph container shrinks, but the graph nodes can still be partially hidden behind the sidebar. The `zoomToFit` fires after a 400ms delay (to wait for the 300ms CSS transition) but it's unreliable — `ForceGraph2D` may not have re-measured its canvas by then. Possible fixes: (1) listen for the `transitionend` CSS event on the panel element instead of using a timeout, (2) use `ForceGraph2D`'s `onResize` callback if available, (3) switch to explicit width props calculated from container measurement rather than relying on auto-detection.
