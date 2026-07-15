# 📊 Data Layer & KPI Cheatsheet

When performing Exploratory Data Analysis (EDA) or Data Quality checks on Databricks Delta Tables, **never** loop over columns one-by-one (this triggers N separate Spark jobs). Always use single-pass aggregations.

## 1. The Highly Optimized PySpark EDA Script
Use this pattern to compute nulls, distinct counts, and skewness for all columns in a single Spark job.

```python
from pyspark.sql import functions as F
from pyspark.sql.types import NumericType

def profile_delta_table(table_name: str):
    df = spark.table(table_name)
    total_rows = df.count()

    numeric_cols = [f.name for f in df.schema.fields if isinstance(f.dataType, NumericType)]
    all_cols = df.columns

    agg_exprs = []
    for c in all_cols:
        # Get Null Counts
        agg_exprs.append(F.count(F.when(F.col(c).isNull(), c)).alias(f"{c}__null_count"))
        # Get Distinct Counts efficiently (1% error margin is fine for EDA)
        agg_exprs.append(F.approx_count_distinct(F.col(c), rsd=0.01).alias(f"{c}__distinct_count"))

    for c in numeric_cols:
        # Skewness is only valid for numeric types
        agg_exprs.append(F.skewness(F.col(c)).alias(f"{c}__skewness"))

    # Execute all aggregations in a single pass
    agg_row = df.agg(*agg_exprs).collect()[0].asDict()

    results = []
    for c in all_cols:
        null_count = agg_row[f"{c}__null_count"]
        distinct_count = agg_row[f"{c}__distinct_count"]
        skew = agg_row.get(f"{c}__skewness")
        results.append({
            "column": c,
            "total_rows": total_rows,
            "null_count": null_count,
            "null_pct": round((null_count / total_rows) * 100, 2) if total_rows else None,
            "distinct_count": distinct_count,
            "skewness": round(skew, 4) if skew is not None else None,
            "is_numeric": c in numeric_cols
        })

    return spark.createDataFrame(results)

# Execute the profiler
profile_df = profile_delta_table("catalog.schema.your_table")
display(profile_df)
```

## 2. Leveraging Delta's Persisted Statistics
If the table is massive and you want an instant baseline before running the full profile, leverage Delta's CBO statistics:

```python
# Force compute statistics into the catalog
spark.sql(f"ANALYZE TABLE catalog.schema.your_table COMPUTE STATISTICS FOR ALL COLUMNS")

# Retrieve instant stats without a heavy scan
stats_df = spark.sql(f"DESCRIBE EXTENDED catalog.schema.your_table")
display(stats_df)
```

## 3. Advanced Data Quality Filters (PySpark)
If you find anomalies (like nulls in critical business columns), use window functions to deduplicate or filter dirty data to expose the culprits to the user:

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import col, row_number

# Identify Dirty Data
dataDQClean = df.filter("critical_column IS NOT NULL")
dataDqError = df.subtract(dataDQClean)

# Find Latest Records (Deduplication)
dataWindowSpec = Window.partitionBy("primary_key_id").orderBy(col("updated_at").desc())
findLatest = dataDQClean.withColumn("row_number", row_number().over(dataWindowSpec))\
    .filter("row_number = 1").drop("row_number")

print(f"DQ Errors: {dataDqError.count()}, Clean: {dataDQClean.count()}, Latest Deduped: {findLatest.count()}")
```
