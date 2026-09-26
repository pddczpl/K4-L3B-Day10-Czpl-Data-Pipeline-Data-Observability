from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report


def auto_heal_pipeline() -> dict:
    """Self-healing pipeline:
    1. Inspects the current clean dataset using Great Expectations 1.x Quality Gate.
    2. If the quality gate FAILS, automatically triggers idempotent repair from trusted raw records.
    3. Rebuilds the vector index and re-validates quality.
    4. Returns status report.
    """
    settings = load_settings()
    run_date = now_utc()
    
    print("=" * 60)
    print("AUTONOMOUS SELF-HEALING DATA PIPELINE (BONUS B2)")
    print("=" * 60)
    
    # Step 1: Check current clean dataset
    print("\n[Self-Healing] Step 1: Checking current dataset quality...")
    if not settings.paths.clean_json.exists():
        print("  WARNING: Clean dataset not found. Triggering initial ingestion & repair...")
        needs_healing = True
        df = None
    else:
        df = pd.read_json(settings.paths.clean_json)
        quality = run_data_quality_checks(df, settings, "pre_heal_check")
        freshness = build_freshness_report(df, settings, settings.paths.quality_dir / "pre_heal_freshness.json")
        needs_healing = not (quality["success"] and freshness["is_fresh"])
        print(f"  Quality Gate: {'PASS' if quality['success'] else 'FAIL'}")
        print(f"  Freshness SLA: {'PASS' if freshness['is_fresh'] else 'FAIL'}")

    if not needs_healing:
        print("\n[Self-Healing] Result: Data pipeline is healthy! No self-healing required.")
        return {"status": "healthy", "action_taken": "none"}

    # Step 2: Auto-repair triggered!
    print("\n[Self-Healing] Step 2: ANOMALY DETECTED! Activating autonomous repair...")
    records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(records, run_date)
    
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=True)
    # Also overwrite the active clean files
    write_csv(df_repaired, settings.paths.clean_csv)
    df_repaired.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=True)
    print(f"  Repaired {len(df_repaired)} records from raw lineage.")

    # Step 3: Re-index
    print("\n[Self-Healing] Step 3: Rebuilding vector index on repaired data...")
    repaired_index = LocalEmbeddingIndex.build(
        df_repaired, settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    # Step 4: Re-evaluate quality gate
    print("\n[Self-Healing] Step 4: Re-verifying quality gate after repair...")
    post_quality = run_data_quality_checks(df_repaired, settings, "post_heal_check")
    post_freshness = build_freshness_report(df_repaired, settings, settings.paths.quality_dir / "post_heal_freshness.json")

    success = post_quality["success"] and post_freshness["is_fresh"]
    print(f"  Post-repair Quality Gate: {'PASS' if post_quality['success'] else 'FAIL'}")
    print(f"  Post-repair Freshness SLA: {'PASS' if post_freshness['is_fresh'] else 'FAIL'}")
    print(f"\n[Self-Healing] Autonomous recovery {'SUCCESSFUL' if success else 'FAILED'}!")
    print("=" * 60)

    return {
        "status": "healed" if success else "heal_failed",
        "action_taken": "repaired_from_raw",
        "records_repaired": len(df_repaired),
        "quality_gate_passed": success,
    }


if __name__ == "__main__":
    auto_heal_pipeline()
