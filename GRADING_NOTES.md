# Phase 2 Grading — Quality Notes

Living after-action report for the deterministic percentile-based scoring formula
introduced in Phase 2. This file captures observations from the first full run,
flags issues that aren't blocking but should inform tuning, and seeds the
Phase 3 ML decision.

> Generate the data behind this file with `just validate` (text-only) or
> `just validate-png` (also drops a histogram at `api/models/grade_distribution.png`).

---

## Headline numbers — first full run

Active version: `v1.0.20260426.211823`, 11,475 grades.

| stat | value | healthy range | verdict |
|---|---:|---|---|
| Mean composite | **48.4** | 50–65 | ⚠️ slightly below |
| Median composite | 48.3 | — | tracks the mean |
| Stddev | 25.4 | wide enough | ✓ |
| A-grade share | 9.8 % | ≥ 5 % | ✓ |
| F-grade share | **39.4 %** | ≥ 5 % | ✓ on the floor — but very heavy |
| Largest letter share | F = 39.4 % | ≤ 40 % | ✓ just under |
| Complete / in-progress | 5,873 / 5,602 | — | roughly half each |

The distribution is skewed left — a U-shape with a much heavier F-side than
A-side. Visible in `models/grade_distribution.png`.

## Letter distribution

| grade | n | pct |
|---|---:|---:|
| A | 1,121 | 9.8 % |
| B+ | 576 | 5.0 % |
| B | 818 | 7.1 % |
| C+ | 902 | 7.9 % |
| C | 930 | 8.1 % |
| D | 2,606 | 22.7 % |
| F | 4,522 | 39.4 % |

## Per-position composite stats

| group | n | mean | median | stddev |
|---|---:|---:|---:|---:|
| GK | 769 | 44.3 | 40.6 | 28.0 |
| DEF | 3,512 | 49.1 | 49.9 | 24.7 |
| MID | 3,345 | 48.9 | 49.1 | 25.1 |
| FWD | 3,849 | 48.3 | 47.3 | 25.7 |

Position groups are consistent with each other — no obvious bias against MIDs
or FWDs at the aggregate level (the [Rodri-tier follow-up](#follow-ups) is about
*specific* defensive midfielders, not the group average). GKs trail by ~5 points,
likely because production is NULL for them (the redistribution pulls more weight
to the volatile financial_return component).

## Component coverage and means

| component | coverage | mean | stddev | reading |
|---|---:|---:|---:|---|
| minutes | 69.4 % | 50.00 | 28.87 | percentile rank — exactly centered ✓ |
| production | 64.9 % | 50.00 | 28.77 | percentile rank — exactly centered ✓ |
| value_trajectory | 99.9 % | 56.00 | 35.86 | sigmoid — slightly bullish, very wide |
| **financial_return** | **51.2 %** | **28.72** | **34.43** | **sigmoid — strongly bearish** |

The minutes and production component scores look healthy: percentile rank with
mean-rank semantics gives a flat distribution centered at 50, exactly as designed.

The sigmoid components are the issue:
- `value_trajectory` is mostly fine — mean 56 with a wide spread.
- `financial_return` averages **28.7**. That's the dominant pull-down on the
  composite. With `sigmoid_scales.financial_return = 2.0`, an
  `exit_ratio_vs_expected` of just −0.5 produces a score of ~27. Many real-world
  exit ratios fall well below the calibrated peer-group expectation, especially
  for older players or players sold during contract decay — the sigmoid is
  amplifying that into very low component scores, which then drag composites
  toward F.

## Hypotheses & tuning candidates

1. **`sigmoid_scales.financial_return` is too aggressive (2.0).** Try 1.0 or 0.5
   to soften the curve. Selling for 50 % less than expected currently maps to
   ~27; with scale 1.0 it becomes ~38 (still bad, less catastrophic).

2. **Calibrated peer-group expectations may be optimistic.** Defaults for
   `default_value_rates` are bullish for under-25s. If the calibration data is
   biased toward high-profile (read: appreciating) players, real-world exits
   under-perform expectations almost universally → low financial_return → F's.
   Re-examine `_populate_expected_exit_ratios` peer matching and consider
   widening or tightening the bands.

3. **The peer group fallback to position-only is firing too often.** With
   matching on age_at_transfer + age_at_departure (each ±2y → ±5y → fallback),
   the position-only fallback has a much wider distribution. A transfer comparing
   itself against the entire position group's exit-ratio distribution will tend
   to under-perform the group's high-fee outliers. Inspect what fraction of
   transfers hit the fallback path.

4. **The Álvarez-style misclassified loan-back fix from earlier shifted the
   mean.** Before that fix, the bimodal distribution had a heavier A tail (many
   in-progress transfers benefiting from extreme value_trajectory sigmoid). Post
   fix, those got their real exit fees attached — and the financial_return
   component frequently scored low. Verify with a curated list whether the
   resulting grades are now *more* defensible despite the headline mean drop.

## Spot checks (curated transfers)

Once tuning is attempted, validate against this list — these are widely
considered good signings, regardless of whether the model agrees today:

- Julián Álvarez → Manchester City (€21M, sold for €75M to Atlético) — currently **B+ 80**
  after the loan-back fix, before any tuning. ✓
- Rodri → Manchester City (€70M, in progress) — flagged in the **["Tune transfer-grading
  model" follow-up](#follow-ups)** as currently grading poorly despite winning the
  Ballon d'Or.
- Erling Haaland → Manchester City — pending verification after tuning.
- Jude Bellingham → Real Madrid — pending verification.
- Bukayo Saka academy contract is excluded (not a paid permanent transfer).

## Architectural observations for Phase 3

- **The percentile components are working as designed** — flat, centered at
  50. There's no signal-vs-noise issue with them.
- **The sigmoid components are too sensitive at typical real-world deltas.**
  Tuning the scale factors will help but won't structurally fix the issue.
- **Sub-position information is being thrown away** in production scoring.
  Defensive midfielders are scored against creative midfielders' G+A/90, which
  dominates. Phase 3 should consider sub-position-aware comparison groups
  (DM vs CM vs AM) and/or weighting production differently per sub-position.
- **Football Manager attribute integration** would let an ML model learn that
  e.g. a high-tackles, high-interceptions DM with low G+A is *good*, instead
  of inferring "low G+A = bad MID".
- The **`phase3_ml_model_path` hook** in `scoring_config.json` is already
  wired so an ML model can override the composite without changing
  the API/UI/explanation surfaces.

## Recommendation for Phase 3

The percentile-based components (minutes, production) produce signal-rich
inputs. The bottleneck is on the financial_return + value_trajectory side, not
the percentile side. A gradient-boosted tree trained on (Football Manager
attributes + the five Phase-2 component scores + sub-position) is likely to
outperform the deterministic composite especially for defensive players and
in-progress transfers, because it can learn that:

- DM/CB-archetype players don't need G+A to be "good" if minutes ≫ peer
- Sub-31% market-value depreciation is below expectation but not catastrophic
- Premium-tier signings should be judged against premium-tier outcomes, not
  the long-tail position-only fallback

Suggested concrete plan:
1. Run the [Rodri tuning follow-up](#follow-ups) first to see how much can be
   recovered with config-only changes (scale factors, weights).
2. If the curated list still has obvious misses, ship the ML path as the
   composite-replacement layer described in `task-04-model-training.md` §
   "Phase 3 ML path."

## Follow-ups

These were spawned during Phase 2 development; treat this list as the canonical
backlog rather than chip ordering:

- **Tune transfer-grading model — Rodri-tier signings shouldn't grade poorly.**
  Audit the financial_return + value_trajectory components, consider
  sub-position-aware production buckets, validate against a curated list of
  10 known-good signings.
- **Add fee/price filter to the Grades page.** Spec called for a fee-range
  control; shipped without it for scope. API + types already accept it.
- **Add tests for appearance ingest + new player fields.** No regression net for
  Task 1 ingestion.
- **Promote shared CSV ingest helpers to public module.** The cross-module
  imports of leading-underscore names from `pipeline.ingest` violate Python
  convention.
- **Make appearances `competition_id` schema-optional.** Currently REQUIRED;
  rename upstream would abort the whole pipeline.
- **Switch appearances upsert to `INSERT ... ON CONFLICT`.** ~300 MB memory
  cost at full-data scale from the dedup-dict pattern; ON CONFLICT also fixes
  the silent data loss on intra-CSV duplicates and the partial change-detection
  bug.
- **Include club/comp/date in appearance change-detection.** Currently only the
  per-match stats are compared.
- **Fix silent data loss on duplicate `(player, game)` keys.** Sentinel-id of
  -1 makes intra-CSV duplicate updates a no-op — can be addressed inline with
  the ON CONFLICT refactor.

---

*Generated 2026-04-26 from the v1.0.20260426.211823 grading run. Re-run
`just validate` after any scoring tweaks and append findings here rather than
overwriting — this is intended as a chronological log.*

---

## Iteration: post-sub-position-aware scoring (no config tune yet)

Active version: `v1.0.20260428.002343`, 11475 grades.

```
================================================================
Grade distribution validation
================================================================
Active version: v1.0.20260428.002343  (11475 grades, scored 2026-04-28 00:23 UTC)

Mean:    48.42
Median:  48.39
Stddev:  25.52
Complete vs in-progress: 5873 / 5602

Letter distribution:
grade  n     pct     bar
-----  ----  ------  -------------------
A      1150   10.0%  █████
B+     569     5.0%  ██
B      814     7.1%  ███
C+     907     7.9%  ███
C      904     7.9%  ███
D      2583   22.5%  ███████████
F      4548   39.6%  ███████████████████

Per-position composite stats:
pg   n     mean   median  stddev
---  ----  -----  ------  ------
GK   769   44.28  40.57   27.97
DEF  3512  49.04  49.94   24.86
MID  3345  48.88  49.17   25.34
FWD  3849  48.28  47.29   25.68

Component scores:
component         n      coverage  nulls  mean   stddev
----------------  -----  --------  -----  -----  ------
minutes           7968    69.4%    3507   50.00  28.87
production        7446    64.9%    4029   50.00  28.76
value_trajectory  11465   99.9%    10     56.00  35.86
financial_return  5871    51.2%    5604   28.72  34.43

WARNINGS:
  - Mean composite (48.4) outside healthy range (50.0, 65.0). Calibrated rates or sigmoid scales may need adjustment.
```

Notes: sub-position-aware production scoring + fee-tier thresholds applied
in T11. Distribution shift vs the prior run reflects whatever the structural
change buys us; subsequent tasks (T13–T16) will tune from this baseline.

---

## Curated gate — baseline (post-T11, pre-tune)

Run with `just curated`. Gate threshold: composite ≥ 78 (B+) for 8 of 10 transfers.

```
PLAYER                           GRADE   COMPOSITE  STATUS
----------------------------------------------------------------------
Rodri → Man City 2019            ?               —  NOT FOUND in DB
Kanté → Chelsea 2016             ?               —  NOT FOUND in DB
De Bruyne → Man City 2015        C+           66.6  FAIL
Bellingham → Real Madrid 2023    C+           62.6  FAIL
Van Dijk → Liverpool 2018        ?               —  NOT FOUND in DB
Cancelo → Man City 2019          D            42.1  FAIL
Alisson → Liverpool 2018         ?               —  NOT FOUND in DB
Haaland → Man City 2022          A            89.9  PASS
Salah → Liverpool 2017           ?               —  NOT FOUND in DB
Álvarez → Man City 2022          ?               —  NOT FOUND in DB
----------------------------------------------------------------------
Curated gate: 1/10 >= B+   ✗ FAILING
Misses:
  - Rodri → Man City 2019 (not found)
  - Kanté → Chelsea 2016 (not found)
  - De Bruyne → Man City 2015 (C+ 66.6)
  - Bellingham → Real Madrid 2023 (C+ 62.6)
  - Van Dijk → Liverpool 2018 (not found)
  - Cancelo → Man City 2019 (D 42.1)
  - Alisson → Liverpool 2018 (not found)
  - Salah → Liverpool 2017 (not found)
  - Álvarez → Man City 2022 (not found)
```

Notes: this is the curated-list snapshot before any config tuning. Whatever
this shows is the "structural fix only" baseline; T13+ will tune from here.

### Curated lookup fix — corrected baseline

The 6 "NOT FOUND" rows above were lookup-script bugs, not missing data. Transfermarkt
stores `Liverpool Football Club` (not `Liverpool FC`), `Rodri` (single-name), `Alisson`,
and `Julián Alvarez` (no accent on the 'á' in Álvarez). After fixing the substrings:

```
PLAYER                           GRADE   COMPOSITE  STATUS
----------------------------------------------------------------------
Rodri → Man City 2019            C+           67.6  FAIL
Kanté → Chelsea 2016             D            51.6  FAIL
De Bruyne → Man City 2015        C+           66.6  FAIL
Bellingham → Real Madrid 2023    C+           62.6  FAIL
Van Dijk → Liverpool 2018        B+           80.2  PASS
Cancelo → Man City 2019          D            42.1  FAIL
Alisson → Liverpool 2018         F            39.9  FAIL
Haaland → Man City 2022          A            89.9  PASS
Salah → Liverpool 2017           A            94.2  PASS
Álvarez → Man City 2022          ?               —  TRANSFER UNGRADED (loan/free?)
----------------------------------------------------------------------
Curated gate: 3/10 >= B+   ✗ FAILING
```

True baseline: 3/10 passing (Van Dijk B+, Haaland A, Salah A). Need to reach 8/10.

Notable failures to track:
- **Rodri C+ 67.6** — the named test case from GRADING_NOTES headline. Sub-position (DM)
  bucketing nudged him slightly but he's still ~10 points short of B+. Expected to be the
  primary beneficiary of T13's sigmoid tuning.
- **Kanté D 51.6** — another DM. Confirms the DM gap isn't just one transfer.
- **Cancelo D 42.1** — FB sub-position. Short stint may be hurting him; may need T15's peer-matching audit.
- **Alisson F 39.9** — premium GK signing. GK keeps `position_group` (no sub-position split per design).
  Likely value_trajectory or financial_return is the killer; sigmoid tuning should help.
- **Álvarez "ungraded"** — loan-classification quirk noted in original GRADING_NOTES. Out of scope.

### Per-transfer expected_floor (gate v2)

User pushback during T12 review: Bellingham (in-progress) and Cancelo (sold ~38% of entry fee)
genuinely SHOULD grade lower than B+. Rather than tuning the model to artificially lift them,
the gate now uses per-transfer `expected_floor`:

- Bellingham 2023: floor C (55) — in-progress, financial_return null
- Cancelo 2019:  floor D (40) — sold for ~€25M of €65M entry fee
- All other 8: floor B+ (78)

Gate passes when **every** transfer clears its own floor.

Also fixed: Álvarez 2022 lookup was returning the €0 follow-up row (ungraded) instead of
the €21.4M Winter 2022 paid signing (graded 80.39). Lookup now orders by composite_score
DESC NULLS LAST so the graded match wins.

```
PLAYER                           FLOOR GRADE   COMPOSITE  STATUS
----------------------------------------------------------------------------
Rodri → Man City 2019            B+    C+           67.6  FAIL
Kanté → Chelsea 2016             B+    D            51.6  FAIL
De Bruyne → Man City 2015        B+    C+           66.6  FAIL
Bellingham → Real Madrid 2023    C     C+           62.6  PASS
Van Dijk → Liverpool 2018        B+    B+           80.2  PASS
Cancelo → Man City 2019          D     D            42.1  PASS
Alisson → Liverpool 2018         B+    F            39.9  FAIL
Haaland → Man City 2022          B+    A            89.9  PASS
Salah → Liverpool 2017           B+    A            94.2  PASS
Álvarez → Man City 2022          B+    B+           80.4  PASS
----------------------------------------------------------------------------
Curated gate: 6/10 clear their per-transfer floor   ✗ FAILING
```

True post-T11 baseline: **6/10 passing**. Four to lift via tuning:

| Transfer | Position | Composite | Floor | Gap |
|---|---|---:|---:|---:|
| Rodri → Man City 2019 | MID (DM) | 67.6 | 78 | 10.4 |
| Kanté → Chelsea 2016 | MID (DM) | 51.6 | 78 | 26.4 |
| De Bruyne → Man City 2015 | MID (CM/AM) | 66.6 | 78 | 11.4 |
| Alisson → Liverpool 2018 | GK | 39.9 | 78 | 38.1 |

Three midfielders + one GK. The DM split helped Rodri less than expected; Kanté is the
biggest miss. Alisson (F) needs structural attention — GK doesn't get sub-position split,
so the F is likely driven by financial_return / value_trajectory sigmoid.

---

## Iteration 1: financial_return sigmoid 2.0 → 1.0

**Config diff:** `sigmoid_scales.financial_return`: 2.0 → 1.0

### Validate output

```
Active version: v1.0.20260428.004633  (11475 grades, scored 2026-04-28 00:46 UTC)

Mean:    49.33
Median:  49.53
Stddev:  24.75
Complete vs in-progress: 5873 / 5602

Letter distribution:
grade  n     pct     bar
-----  ----  ------  ------------------
A      1065    9.3%  ████
B+     605     5.3%  ██
B      886     7.7%  ███
C+     1025    8.9%  ████
C      987     8.6%  ████
D      2559   22.3%  ███████████
F      4348   37.9%  ██████████████████

Per-position composite stats:
pg   n     mean   median  stddev
---  ----  -----  ------  ------
GK   769   45.20  42.25   27.21
DEF  3512  49.80  50.00   24.22
MID  3345  49.83  50.00   24.47
FWD  3849  49.28  48.60   24.89

Component scores:
component         n      coverage  nulls  mean   stddev
----------------  -----  --------  -----  -----  ------
minutes           7968    69.4%    3507   50.00  28.87
production        7446    64.9%    4029   50.00  28.76
value_trajectory  11465   99.9%    10     56.00  35.86
financial_return  5871    51.2%    5604   34.26  29.10

WARNINGS:
  - Mean composite (49.3) outside healthy range (50.0, 65.0). Calibrated rates or sigmoid scales may need adjustment.
```

### Curated lookup

```
PLAYER                           FLOOR GRADE   COMPOSITE  STATUS
----------------------------------------------------------------------------
Rodri → Man City 2019            B+    C+           67.6  FAIL
Kanté → Chelsea 2016             B+    D            54.2  FAIL
De Bruyne → Man City 2015        B+    C+           67.6  FAIL
Bellingham → Real Madrid 2023    C     C+           62.6  PASS
Van Dijk → Liverpool 2018        B+    B+           80.2  PASS
Cancelo → Man City 2019          D     D            44.5  PASS
Alisson → Liverpool 2018         B+    F            39.9  FAIL
Haaland → Man City 2022          B+    A            89.9  PASS
Salah → Liverpool 2017           B+    A            94.2  PASS
Álvarez → Man City 2022          B+    B            77.2  FAIL
----------------------------------------------------------------------------
Curated gate: 5/10 clear their per-transfer floor   ✗ FAILING

Non-B+ floors:
  - Bellingham → Real Madrid 2023: floor C (55) — in-progress, financial_return null
  - Cancelo → Man City 2019: floor D (40) — sold ~38% of entry fee, age-adjusted poor

Misses:
  - Rodri → Man City 2019 (C+ 67.6, floor B+ 78)
  - Kanté → Chelsea 2016 (D 54.2, floor B+ 78)
  - De Bruyne → Man City 2015 (C+ 67.6, floor B+ 78)
  - Alisson → Liverpool 2018 (F 39.9, floor B+ 78)
  - Álvarez → Man City 2022 (B 77.2, floor B+ 78)
```

### Verdict

Distribution gates fail (mean 49.33 still under [50, 65]); curated 6/10 → 5/10 (Álvarez regressed PASS→FAIL). Continue to T14 (further config tune).

---

## Iteration: tenure-success floor on value_trajectory + financial_return

**Why:** in-progress GKs and long-tenure starters with poor exit fees were
getting D/F grades despite minutes + tenure being the success signal the
percentile components couldn't see. Heuristic stopgap until Phase 3 (FM data + ML).

**Config:** `tenure_success_floor`: min_tenure_days=1460 (4y), min_minutes_pct=70, floor_score=70

### Validate

```
Active version: v1.0.20260428.010424  (11475 grades, scored 2026-04-28 01:04 UTC)

Mean:    49.51
Median:  49.74
Stddev:  24.87
Complete vs in-progress: 5873 / 5602

Letter distribution:
grade  n     pct     bar
-----  ----  ------  ------------------
A      1077    9.4%
B+     649     5.7%
B      902     7.9%
C+     1008    8.8%
C      972     8.5%
D      2527   22.0%
F      4340   37.8%

Per-position composite stats:
pg   n     mean   median  stddev
---  ----  -----  ------  ------
GK   769   46.15  43.98   27.77
DEF  3512  49.97  50.00   24.35
MID  3345  49.97  50.00   24.57
FWD  3849  49.35  48.61   24.95

Component scores:
component         n      coverage  nulls  mean   stddev
----------------  -----  --------  -----  -----  ------
minutes           7968    69.4%    3507   50.00  28.87
production        7446    64.9%    4029   50.00  28.76
value_trajectory  11465   99.9%    10     56.24  35.78
financial_return  5871    51.2%    5604   35.01  29.44

WARNINGS:
  - Mean composite (49.5) outside healthy range (50.0, 65.0).
```

### Curated

```
PLAYER                           FLOOR GRADE   COMPOSITE  STATUS
----------------------------------------------------------------------------
Rodri → Man City 2019            B+    C+           67.6  FAIL
Kanté → Chelsea 2016             B+    D            54.2  FAIL
De Bruyne → Man City 2015        B+    C+           67.6  FAIL
Bellingham → Real Madrid 2023    C     C+           62.6  PASS
Van Dijk → Liverpool 2018        B+    B+           80.9  PASS
Cancelo → Man City 2019          D     D            44.5  PASS
Alisson → Liverpool 2018         B+    B            73.5  FAIL
Haaland → Man City 2022          B+    A            89.9  PASS
Salah → Liverpool 2017           B+    A            94.2  PASS
Álvarez → Man City 2022          B+    B            77.2  FAIL
----------------------------------------------------------------------------
Curated gate: 5/10 clear their per-transfer floor   ✗ FAILING

Misses:
  - Rodri → Man City 2019 (C+ 67.6, floor B+ 78)
  - Kanté → Chelsea 2016 (D 54.2, floor B+ 78)
  - De Bruyne → Man City 2015 (C+ 67.6, floor B+ 78)
  - Alisson → Liverpool 2018 (B 73.5, floor B+ 78)
  - Álvarez → Man City 2022 (B 77.2, floor B+ 78)
```

### Verdict

Curated 5/10 → 5/10 (no change). Distribution mean barely lifted (49.33 → 49.51) and the long-tenure misses (Kanté, Alisson, De Bruyne, Rodri) still sit below B+ — the 70-floor on two components doesn't drag the composite past 78 when the other halves (production for in-progress GK, financial_return for sub-€0 exits) remain weak. Continue to T15 peer-matching audit; the floor helps but doesn't solve composite-level pass-through.
