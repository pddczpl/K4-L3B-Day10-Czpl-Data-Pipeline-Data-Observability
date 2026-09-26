from __future__ import annotations

from datetime import datetime, timezone


def main() -> None:
    from core.config import load_settings
    from core.utils import now_utc, read_json, write_csv, write_json
    from ingestion.crossref import fetch_source_records, load_raw_records
    from ingestion.cleaning import build_clean_dataframe
    from retrieval.index import LocalEmbeddingIndex
    from evaluation.testset import build_test_set
    from evaluation.metrics import evaluate_pipeline
    from observability.quality import run_data_quality_checks, build_freshness_report
    from observability.reporting import generate_phase1_report
    
    print("=" * 60)
    print("PHASE 1: Baseline Pipeline")
    print("=" * 60)
    
    # 1. Load settings
    settings = load_settings()
    run_date = now_utc()
    
    # 2. Fetch or load raw records
    print("\n[Step 1] Loading raw records...")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"  Loaded {len(records)} raw records.")
    
    # 3. Clean data
    print("\n[Step 2] Cleaning data...")
    df = build_clean_dataframe(records, run_date)
    print(f"  Clean dataframe: {len(df)} rows.")
    
    # 4. Save clean artifacts
    print("\n[Step 3] Saving clean artifacts...")
    write_csv(df, settings.paths.clean_csv)
    # For JSON, convert to records and handle types
    df_json = df.copy()
    # Convert list columns properly
    df_json.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=True)
    print(f"  Saved: {settings.paths.clean_csv}")
    print(f"  Saved: {settings.paths.clean_json}")
    
    # 5. Build ChromaDB index
    print("\n[Step 4] Building ChromaDB index...")
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=settings.paths.embeddings_json)
    print(f"  Indexed {len(df)} documents into '{settings.baseline_collection_name}'.")
    
    # 6. Build or load test set
    print("\n[Step 5] Building evaluation test set...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    print(f"  Test set: {len(test_set)} questions.")
    
    # 7. Evaluate
    print("\n[Step 6] Evaluating baseline pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"  Retrieval Hit Rate: {metrics['retrieval_hit_rate']:.4f}")
    print(f"  Mean Token F1: {metrics['mean_token_f1']:.4f}")
    
    # 8. Quality checks & freshness
    print("\n[Step 7] Running data quality checks...")
    quality = run_data_quality_checks(df, settings, "baseline")
    print(f"  Quality check: {'PASS' if quality['success'] else 'FAIL'}")
    
    print("\n[Step 8] Building freshness report...")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"  Freshness SLA: {'PASS' if freshness['is_fresh'] else 'FAIL'}")
    
    # 9. Generate report
    print("\n[Step 9] Generating Phase 1 report...")
    source_summary = {
        "api": settings.source_api,
        "query": settings.source_query,
        "total_records": len(records),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality,
        freshness=freshness,
    )
    print(f"  Report saved: {settings.paths.baseline_report}")
    
    print("\n" + "=" * 60)
    print("PHASE 1 COMPLETE")
    print("=" * 60)
