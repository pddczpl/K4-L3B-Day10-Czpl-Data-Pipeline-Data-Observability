from __future__ import annotations


def main() -> None:
    import pandas as pd
    
    from core.config import load_settings
    from core.utils import now_utc, read_json, write_csv
    from ingestion.crossref import load_raw_records
    from ingestion.cleaning import build_clean_dataframe
    from ingestion.corruption import corrupt_clean_dataframe
    from retrieval.index import LocalEmbeddingIndex
    from evaluation.metrics import evaluate_pipeline
    from observability.quality import run_data_quality_checks, build_freshness_report
    from observability.reporting import generate_corruption_report
    
    print("=" * 60)
    print("PHASE 2: Corruption -> Evaluate -> Repair -> Compare")
    print("=" * 60)
    
    settings = load_settings()
    run_date = now_utc()
    
    # 1. Load baseline metrics
    print("\n[Step 1] Loading baseline metrics...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"  Baseline Hit Rate: {baseline_metrics['retrieval_hit_rate']:.4f}")
    
    # 2. Load clean dataset
    print("\n[Step 2] Loading clean dataset...")
    df_clean = pd.read_json(settings.paths.clean_json)
    print(f"  Clean rows: {len(df_clean)}")
    
    # 3. Corrupt
    print("\n[Step 3] Corrupting data...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    print(f"  Corrupted rows: {len(df_corrupted)}")
    
    # 4. Save corrupted artifacts
    print("\n[Step 4] Saving corrupted artifacts...")
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=True)
    
    # 5. Rebuild index on corrupted data & evaluate
    print("\n[Step 5] Building corrupted index & evaluating...")
    corrupted_index = LocalEmbeddingIndex.build(
        df_corrupted, settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"  Corrupted Hit Rate: {corrupted_metrics['retrieval_hit_rate']:.4f}")
    print(f"  Corrupted Mean Token F1: {corrupted_metrics['mean_token_f1']:.4f}")
    
    # 6. Quality checks on corrupted data
    print("\n[Step 6] Quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings,
        settings.paths.quality_dir / "corrupted_freshness_report.json",
    )
    print(f"  Corrupted Quality: {'PASS' if corrupted_quality['success'] else 'FAIL'}")
    
    # 7. Repair from raw records
    print("\n[Step 7] Repairing data from raw records...")
    records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(records, run_date)
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=True)
    print(f"  Repaired rows: {len(df_repaired)}")
    
    # 8. Rebuild index on repaired data & evaluate
    print("\n[Step 8] Building repaired index & evaluating...")
    repaired_index = LocalEmbeddingIndex.build(
        df_repaired, settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f"  Repaired Hit Rate: {repaired_metrics['retrieval_hit_rate']:.4f}")
    
    # 9. Quality checks on repaired data
    print("\n[Step 9] Quality checks on repaired data...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        df_repaired, settings,
        settings.paths.quality_dir / "repaired_freshness_report.json",
    )
    
    # 10. Comparison report
    print("\n[Step 10] Generating comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"  Report saved: {settings.paths.comparison_report}")
    
    # Print comparison table
    print("\n" + "=" * 60)
    print("3-STATE COMPARISON")
    print("=" * 60)
    print(f"{'Metric':<25} {'Baseline':>12} {'Corrupted':>12} {'Repaired':>12}")
    print("-" * 61)
    for key in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        b = baseline_metrics.get(key, 0)
        c = corrupted_metrics.get(key, 0)
        r = repaired_metrics.get(key, 0)
        print(f"{key:<25} {b:>12.4f} {c:>12.4f} {r:>12.4f}")
    print("=" * 60)
    print("PHASE 2 COMPLETE")
    print("=" * 60)
