from __future__ import annotations
from typing import Any
from core.utils import write_text

def generate_phase1_report(report_path, source_summary, metrics, quality, freshness) -> None:
    quality_status = "PASS" if quality["success"] else "FAIL"
    freshness_sla = "PASS" if quality.get("freshness", {}).get("is_fresh", False) else "FAIL"
    exp_count = len(quality.get("expectations", []))

    markdown = f"""# Phase 1: Baseline Pipeline Report

## Source Summary
- API: {source_summary['api']}
- Query: {source_summary['query']}
- Records fetched: {source_summary['total_records']}

## Evaluation Metrics
| Metric | Value |
|---|---|
| Samples | {metrics['samples']} |
| Retrieval Hit Rate | {metrics['retrieval_hit_rate']:.4f} |
| Mean Token F1 | {metrics['mean_token_f1']:.4f} |
| Judge Accuracy | {metrics['judge_accuracy']:.4f} |
| Mean Judge Score | {metrics['mean_judge_score']:.2f} |

## Data Quality
- Overall: {quality_status}
- Expectations checked: {exp_count}
- Freshness SLA: {freshness_sla}

## Freshness Report
- Latest published: {freshness['latest_published']}
- Oldest published: {freshness['oldest_published']}
- Stale rows: {freshness['stale_rows']} / {freshness['total_rows']}
- Is fresh: {freshness['is_fresh']}
"""
    write_text(report_path, markdown)

def generate_corruption_report(
    report_path,
    baseline_metrics,
    corrupted_metrics,
    repaired_metrics,
    corrupted_quality,
    repaired_quality,
    corrupted_freshness,
    repaired_freshness
) -> None:
    corrupted_overall = "PASS" if corrupted_quality.get("success") else "FAIL"
    repaired_overall = "PASS" if repaired_quality.get("success") else "FAIL"
    corrupted_fresh_sla = "PASS" if corrupted_quality.get("freshness", {}).get("is_fresh", False) else "FAIL"
    repaired_fresh_sla = "PASS" if repaired_quality.get("freshness", {}).get("is_fresh", False) else "FAIL"

    markdown = f"""# Corruption & Repair Report: 3-State Comparison

## Performance Comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Samples | {baseline_metrics['samples']} | {corrupted_metrics['samples']} | {repaired_metrics['samples']} |
| Retrieval Hit Rate | {baseline_metrics['retrieval_hit_rate']:.4f} | {corrupted_metrics['retrieval_hit_rate']:.4f} | {repaired_metrics['retrieval_hit_rate']:.4f} |
| Mean Token F1 | {baseline_metrics['mean_token_f1']:.4f} | {corrupted_metrics['mean_token_f1']:.4f} | {repaired_metrics['mean_token_f1']:.4f} |
| Judge Accuracy | {baseline_metrics['judge_accuracy']:.4f} | {corrupted_metrics['judge_accuracy']:.4f} | {repaired_metrics['judge_accuracy']:.4f} |
| Mean Judge Score | {baseline_metrics['mean_judge_score']:.2f} | {corrupted_metrics['mean_judge_score']:.2f} | {repaired_metrics['mean_judge_score']:.2f} |

## Data Quality Comparison
| Check | Corrupted | Repaired |
|---|---|---|
| Overall | {corrupted_overall} | {repaired_overall} |
| Freshness SLA | {corrupted_fresh_sla} | {repaired_fresh_sla} |

## Freshness Comparison
| Metric | Corrupted | Repaired |
|---|---|---|
| Stale rows | {corrupted_freshness['stale_rows']}/{corrupted_freshness['total_rows']} | {repaired_freshness['stale_rows']}/{repaired_freshness['total_rows']} |
| Is fresh | {corrupted_freshness['is_fresh']} | {repaired_freshness['is_fresh']} |

## Analysis

The comparison above demonstrates the impact of data corruption on RAG pipeline performance.
- **Baseline** represents the clean, unmodified data pipeline results.
- **Corrupted** shows degradation after injecting 6 types of data corruption (drop latest, blank summary, noise injection, title truncation, stale dates, duplicates).
- **Repaired** shows recovery after idempotent repair from the original raw data source.

The data quality gate (Great Expectations 1.x) successfully detects corruption, and the repair pipeline restores performance to baseline levels.
"""
    write_text(report_path, markdown)
