import logging
from django.conf import settings
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


def get_spark_session(app_name: str = "RhombusRegex") -> SparkSession:
    master = getattr(settings, "SPARK_MASTER_URL", "local[*]")
    logger.info(f"Connecting to Spark master: {master}")

    session = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.files.maxPartitionBytes", "134217728")
        .getOrCreate()
    )

    session.sparkContext.setLogLevel("WARN")
    return session
