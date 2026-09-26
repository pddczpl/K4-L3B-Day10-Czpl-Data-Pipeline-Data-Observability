# Corruption & Repair Report: 3-State Comparison

## Performance Comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Samples | 10 | 10 | 10 |
| Retrieval Hit Rate | 1.0000 | 0.5000 | 1.0000 |
| Mean Token F1 | 0.5754 | 0.3306 | 0.5754 |
| Judge Accuracy | 0.5000 | 0.3000 | 0.5000 |
| Mean Judge Score | 3.20 | 2.30 | 3.20 |

## Data Quality Comparison
| Check | Corrupted | Repaired |
|---|---|---|
| Overall | FAIL | PASS |
| Freshness SLA | PASS | PASS |

## Freshness Comparison
| Metric | Corrupted | Repaired |
|---|---|---|
| Stale rows | 0/23 | 0/24 |
| Is fresh | True | True |

## Analysis

The comparison above demonstrates the impact of data corruption on RAG pipeline performance.
- **Baseline** represents the clean, unmodified data pipeline results.
- **Corrupted** shows degradation after injecting 6 types of data corruption (drop latest, blank summary, noise injection, title truncation, stale dates, duplicates).
- **Repaired** shows recovery after idempotent repair from the original raw data source.

The data quality gate (Great Expectations 1.x) successfully detects corruption, and the repair pipeline restores performance to baseline levels.
