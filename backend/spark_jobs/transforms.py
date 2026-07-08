"""
transforms.py — core PySpark regex replacement logic.
"""

import os
import logging
from typing import Callable

from pyspark.sql import functions as F
from pyspark.sql.utils import AnalysisException

from .session import get_spark_session

logger = logging.getLogger(__name__)


def run_replacement(
    upload_path: str,
    target_columns: list[str],
    regex_pattern: str,
    replacement_value: str,
    job_id: str,
    progress_callback: Callable[[int, str], None] | None = None,
) -> tuple[str, int]:

    def _progress(pct: int, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    spark = get_spark_session()
    _progress(35, "SparkSession ready")

    # Verify file exists before attempting to read
    if not os.path.exists(upload_path):
        raise RuntimeError(
            f"Upload file not found at {upload_path}. "
            f"The file may have been lost between upload and processing."
        )

    ext = os.path.splitext(upload_path)[1].lower()

    # Read via pandas first, then convert to Spark DataFrame.
    # This is more reliable than passing file paths to Spark directly,
    # which can fail due to filesystem abstraction differences.
    import pandas as pd

    try:
        if ext == ".csv":
            pdf = pd.read_csv(upload_path, dtype=str).fillna("")
        elif ext in (".xlsx", ".xls"):
            pdf = pd.read_excel(upload_path, dtype=str).fillna("")
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as e:
        raise RuntimeError(f"Could not read file {upload_path}: {e}") from e

    logger.info(f"[Job {job_id}] Read {len(pdf)} rows via pandas")
    _progress(50, f"File loaded — {len(pdf):,} rows")

    # Convert to Spark DataFrame
    df = spark.createDataFrame(pdf)

    # Validate columns
    actual_cols = set(df.columns)
    missing = [c for c in target_columns if c not in actual_cols]
    if missing:
        raise ValueError(
            f"Column(s) not found: {missing}. "
            f"Available: {sorted(actual_cols)}"
        )

    # Apply regex replacement across target columns
    for col_name in target_columns:
        df = df.withColumn(
            col_name,
            F.regexp_replace(F.col(col_name), regex_pattern, replacement_value)
        )

    _progress(75, "Regex replacement applied")

    # Write result
    from django.conf import settings
    result_dir = f"results/{job_id}"
    result_abs_dir = os.path.join(settings.MEDIA_ROOT, result_dir)

    os.makedirs(result_abs_dir, exist_ok=True)

    (
        df.coalesce(1)
        .write
        .mode("overwrite")
        .option("header", "true")
        .csv(result_abs_dir)
    )

    _progress(90, "Results written to disk")

    # Find and rename the part file Spark wrote
    part_file = _find_part_file(result_abs_dir)
    final_path = os.path.join(result_abs_dir, "result.csv")
    os.rename(part_file, final_path)

    row_count = len(pdf)

    relative_path = os.path.join(result_dir, "result.csv")
    _progress(95, f"Done. {row_count:,} rows processed.")
    return relative_path, row_count


def _find_part_file(directory: str) -> str:
    for fname in os.listdir(directory):
        if fname.startswith("part-") and fname.endswith(".csv"):
            return os.path.join(directory, fname)
    raise FileNotFoundError(f"No part file found in Spark output directory: {directory}")
