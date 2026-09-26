from __future__ import annotations
from typing import Any
import pandas as pd
import great_expectations as gx
from great_expectations.expectations import (
    ExpectTableRowCountToBeBetween,
    ExpectColumnValuesToNotBeNull,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValueLengthsToBeBetween,
)
from core.config import Settings
from core.utils import write_json

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"{report_name}_suite")
    suite = context.suites.add(suite)

    # 1. Row count between 1 and 1000
    suite.add_expectation(ExpectTableRowCountToBeBetween(min_value=1, max_value=1000))

    # 2. paper_id not null
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="paper_id"))

    # 3. paper_id unique
    suite.add_expectation(ExpectColumnValuesToBeUnique(column="paper_id"))

    # 4. summary length between 10 and 50000
    suite.add_expectation(ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10, max_value=50000))

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=f"{report_name}_validation",
            data=batch_def,
            suite=suite,
        )
    )
    results = validation_definition.run(batch_parameters={"dataframe": df})

    success = results.success
    result_list = []
    for r in results.results:
        result_list.append({
            "expectation_type": r.expectation_config.type,
            "success": r.success,
            "result": {
                k: v for k, v in (r.result or {}).items()
                if isinstance(v, (str, int, float, bool, type(None)))
            },
        })

    # Freshness check
    freshness_threshold = settings.freshness_threshold_days
    if "age_days" in df.columns:
        stale_count = int((df["age_days"] > freshness_threshold).sum())
        stale_ratio = stale_count / len(df) if len(df) > 0 else 0.0
        is_fresh = stale_ratio <= 0.25
    else:
        stale_count = 0
        stale_ratio = 0.0
        is_fresh = True

    report = {
        "success": bool(success and is_fresh),
        "report_name": report_name,
        "expectations": result_list,
        "freshness": {
            "stale_count": stale_count,
            "stale_ratio": round(stale_ratio, 4),
            "threshold_days": freshness_threshold,
            "is_fresh": is_fresh,
        },
    }

    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, report)

    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    threshold = settings.freshness_threshold_days
    if "age_days" in df.columns and len(df) > 0:
        stale_mask = df["age_days"] > threshold
        stale_rows = int(stale_mask.sum())
        latest_published = str(df["published"].max())
        oldest_published = str(df["published"].min())
    else:
        stale_rows = 0
        latest_published = "N/A"
        oldest_published = "N/A"

    total_rows = len(df)
    is_fresh = (stale_rows / total_rows <= 0.25) if total_rows > 0 else True

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_rows / total_rows, 4) if total_rows > 0 else 0.0,
        "threshold_days": threshold,
        "is_fresh": is_fresh,
    }
    write_json(report_path, payload)
    return payload
