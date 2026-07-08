import os
import logging
from typing import Callable
from pyspark.sql import functions as F
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

    _progress(35, "Loading file")

    import pandas as pd
    ext = os.path.splitext(upload_path)[1].lower()
    if ext == ".csv":
        pdf = pd.read_csv(upload_path, dtype=str).fillna("")
    elif ext in (".xlsx", ".xls"):
        pdf = pd.read_excel(upload_path, dtype=str).fillna("")
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    logger.info(f"[Job {job_id}] Read {len(pdf)} rows via pandas from {upload_path}")
    _progress(50, f"File loaded — {len(pdf):,} rows")

    spark = get_spark_session()
    df = spark.createDataFrame(pdf)

    actual_cols = set(df.columns)
    missing = [c for c in target_columns if c not in actual_cols]
    if missing:
        raise ValueError(f"Column(s) not found: {missing}. Available: {sorted(actual_cols)}")

    for col_name in target_columns:
        df = df.withColumn(
            col_name,
            F.regexp_replace(F.col(col_name), regex_pattern, replacement_value)
        )

    _progress(75, "Regex replacement applied")

    from django.conf import settings
    result_dir = f"results/{job_id}"
    result_abs_dir = os.path.join(settings.MEDIA_ROOT, result_dir)
    os.makedirs(result_abs_dir, exist_ok=True)

    df.coalesce(1).write.mode("overwrite").option("header", "true").csv(result_abs_dir)

    _progress(90, "Results written to disk")

    for fname in os.listdir(result_abs_dir):
        if fname.startswith("part-") and fname.endswith(".csv"):
            os.rename(os.path.join(result_abs_dir, fname), os.path.join(result_abs_dir, "result.csv"))
            break

    row_count = len(pdf)
    relative_path = os.path.join(result_dir, "result.csv")
    _progress(95, f"Done. {row_count:,} rows processed.")
    return relative_path, row_count
