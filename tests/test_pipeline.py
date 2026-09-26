from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest
import pandas as pd

# Add src to path
src_dir = Path(__file__).resolve().parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from core.config import load_settings
from ingestion.crossref import PaperRecord, parse_crossref_payload, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import run_data_quality_checks, build_freshness_report
from evaluation.testset import build_test_set


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def sample_records(settings):
    return load_raw_records(settings.paths.raw_records_json)


@pytest.fixture
def clean_df(sample_records):
    return build_clean_dataframe(sample_records, datetime.now(timezone.utc))


def test_crossref_raw_records_count(sample_records):
    """Test raw records are loaded and count is 24."""
    assert len(sample_records) == 24
    for record in sample_records:
        assert isinstance(record, PaperRecord)
        assert record.paper_id.strip() != ""
        assert record.title.strip() != ""
        assert record.summary.strip() != ""


def test_clean_dataframe_structure(clean_df):
    """Test clean dataframe has expected columns and no duplicates."""
    expected_cols = [
        "paper_id", "title", "summary", "authors", "categories",
        "primary_category", "published", "updated", "abs_url", "pdf_url",
        "age_days", "authors_joined", "categories_joined", "summary_chars",
        "text_for_embedding"
    ]
    for col in expected_cols:
        assert col in clean_df.columns, f"Missing column: {col}"
    
    assert len(clean_df) == 24
    assert clean_df["paper_id"].is_unique
    assert (clean_df["summary_chars"] > 0).all()
    assert (clean_df["text_for_embedding"].str.startswith("Title:")).all()


def test_great_expectations_quality_gate(clean_df, settings):
    """Test GX 1.x quality gate passes on clean data."""
    report = run_data_quality_checks(clean_df, settings, "pytest_baseline")
    assert report["success"] is True
    assert len(report["expectations"]) == 4
    for exp in report["expectations"]:
        assert exp["success"] is True, f"Expectation failed: {exp['expectation_type']}"


def test_freshness_sla(clean_df, settings):
    """Test freshness report calculation."""
    report = build_freshness_report(clean_df, settings, settings.paths.quality_dir / "pytest_freshness.json")
    assert report["total_rows"] == 24
    assert report["is_fresh"] is True
    assert report["stale_rows"] <= report["total_rows"] * 0.25


def test_testset_generation(clean_df, settings, tmp_path):
    """Test test set generates exactly 10 questions across 4 categories."""
    output_path = tmp_path / "test_set.json"
    test_set = build_test_set(clean_df, output_path)
    assert len(test_set) == 10
    
    types = {item["question_type"] for item in test_set}
    assert "summary" in types
    assert "authors" in types
    assert "date" in types
    assert "categories" in types
    
    for item in test_set:
        assert "question" in item
        assert "ground_truth" in item
        assert len(item["ground_truth_doc_ids"]) > 0


def test_data_corruption_and_detection(clean_df, settings, tmp_path):
    """Test corruption modifies data and GX quality gate catches it."""
    log_path = tmp_path / "corruption_log.json"
    corrupted = corrupt_clean_dataframe(clean_df, log_path)
    
    # Quality gate must fail on corrupted data (due to blank summary, duplicates, etc.)
    report = run_data_quality_checks(corrupted, settings, "pytest_corrupted")
    assert report["success"] is False


def test_idempotent_repair(sample_records, settings):
    """Test that repairing from raw data produces identical clean data."""
    run_date = datetime.now(timezone.utc)
    df1 = build_clean_dataframe(sample_records, run_date)
    df2 = build_clean_dataframe(sample_records, run_date)
    assert len(df1) == len(df2)
    assert (df1["paper_id"] == df2["paper_id"]).all()
