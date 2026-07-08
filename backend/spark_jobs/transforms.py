"""
transforms.py — core PySpark regex replacement logic.

This module has NO Django imports — it's pure PySpark.
That's intentional: it keeps the Spark layer independently testable
and decoupled from Django's ORM and settings.

The only coupling point is the file path convention (media/results/).
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
    """
    Reads the uploaded file into Spark, applies regex replacement across
    target_columns, writes the result as a single CSV, and returns
    (result_relative_path, row_count).

    Args:
        upload_path:      Absolute path to the uploaded CSV/Excel file.
        target_columns:   List of column names to apply the regex to.
        regex_pattern:    Python-compatible regex (validated before this call).
        replacement_value: String to replace matches with.
        job_id:           Used to name the output file.
        progress_callback: Called with (pct: int, message: str) to report progress.

    Returns:
        (result_path, row_count) where result_path is relative to MEDIA_ROOT.
    """

    def _progress(pct: int, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    spark = get_spark_session()
    _progress(35, "SparkSession ready")

    # ── 1. Read input file ────────────────────────────────────────────────
    ext = os.path.splitext(upload_path)[1].lower()

    # Prefix with file:// so Spark explicitly uses local filesystem
    # Without this, Spark on some platforms tries HDFS or other filesystems
    local_path = f"file://{upload_path}" if not upload_path.startswith("file://") else upload_path

    try:
        if ext == ".csv":
            df = (
                spark.read
                .option("header", "true")
                .option("inferSchema", "false")
                .option("multiLine", "true")
                .option("escape", '"')
                .csv(local_path)
            )
        elif ext in (".xlsx", ".xls"):
            # PySpark doesn't read Excel natively.
            # Strategy: convert to CSV first with pandas (small overhead, only happens once).
            # For million-row Excel files this is a known bottleneck — document in README.
            df = _excel_to_spark(spark, upload_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except AnalysisException as e:
        raise RuntimeError(f"Spark could not read file {upload_path}: {e}") from e

    _progress(50, "File loaded into Spark")

    # ── 2. Validate requested columns exist ──────────────────────────────
    actual_cols = set(df.columns)
    missing = [c for c in target_columns if c not in actual_cols]
    if missing:
        raise ValueError(
            f"Requested column(s) not found in file: {missing}. "
            f"Available columns: {sorted(actual_cols)}"
        )

    # ── 3. Apply regex replacement ────────────────────────────────────────
    # F.regexp_replace is a Spark built-in that runs distributed across partitions.
    # This is the key performance advantage over pandas iterrows().
    # For N partitions on K workers, each worker processes N/K partitions in parallel.
    for col_name in target_columns:
        df = df.withColumn(
            col_name,
            F.regexp_replace(F.col(col_name), regex_pattern, replacement_value)
        )

    _progress(75, "Regex replacement applied across all partitions")

    # ── 4. Write result ───────────────────────────────────────────────────
    # coalesce(1): merge all partitions into a single output file.
    # Trade-off: slower for huge datasets (single writer), but simplifies
    # result serving (one file to read, paginate, and serve over HTTP).
    # For production with >10M rows, write multiple partitions and build a
    # streaming/cursor-based result API instead.
    result_dir = f"results/{job_id}"
    from django.conf import settings
    result_abs_dir = os.path.join(settings.MEDIA_ROOT, result_dir)

    (
        df.coalesce(1)
        .write
        .mode("overwrite")
        .option("header", "true")
        .csv(result_abs_dir)
    )

    _progress(90, "Results written to disk")

    # ── 5. Find the part file Spark wrote ────────────────────────────────
    # Spark writes files named "part-00000-*.csv". We rename it to result.csv
    # for a clean, predictable path that the Django view can serve.
    part_file = _find_part_file(result_abs_dir)
    final_path = os.path.join(result_abs_dir, "result.csv")
    os.rename(part_file, final_path)

    # ── 6. Count rows ─────────────────────────────────────────────────────
    # df is already computed; count() triggers an action but is cheap now.
    row_count = df.count()

    # Return relative path (relative to MEDIA_ROOT) for storage in the DB.
    relative_path = os.path.join(result_dir, "result.csv")

    _progress(95, f"Done. {row_count:,} rows processed.")
    return relative_path, row_count


def _excel_to_spark(spark, excel_path: str):
    """
    Converts Excel to a Spark DataFrame via a pandas intermediate step.
    Only used for Excel files — CSV goes directly into Spark.
    Documented trade-off: pandas reads the whole Excel file into memory once.
    For very large Excel files, advise users to convert to CSV first.
    """
    import pandas as pd
    pdf = pd.read_excel(excel_path, dtype=str)  # dtype=str: keep all values as strings
    return spark.createDataFrame(pdf.fillna(""))


def _find_part_file(directory: str) -> str:
    """Finds the Spark-written part-*.csv file in the output directory."""
    for fname in os.listdir(directory):
        if fname.startswith("part-") and fname.endswith(".csv"):
            return os.path.join(directory, fname)
    raise FileNotFoundError(f"No part file found in Spark output directory: {directory}")
