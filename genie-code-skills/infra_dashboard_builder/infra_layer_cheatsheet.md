# ⚙️ Infrastructure & Metadata Cheatsheet

When querying Unity Catalog system tables for job reliability, compute costs, or upstream lineage, you must handle edge cases like SCD2 deduplication (Slowly Changing Dimensions) and path-based external tables.

## 1. Job Freshness (`system.lakeflow`)
To check when jobs last ran, you must join `jobs` (to get the latest job definition) with `job_run_timeline` (to get the execution status).

**Query: Find jobs that have not run in 30 days (Stale Jobs)**
```sql
WITH latest_jobs AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY workspace_id, job_id ORDER BY change_time DESC) as rn
    FROM system.lakeflow.jobs QUALIFY rn = 1
),
latest_not_deleted_jobs AS (
    SELECT workspace_id, job_id, name, change_time, tags
    FROM latest_jobs WHERE delete_time IS NULL
),
last_seen_job_timestamp AS (
    SELECT workspace_id, job_id, MAX(period_start_time) as last_executed_at
    FROM system.lakeflow.job_run_timeline
    WHERE run_type = "JOB_RUN"
    GROUP BY ALL
)
SELECT
    t1.workspace_id, t1.job_id, t1.name,
    t1.change_time as last_modified_at,
    t2.last_executed_at,
    t1.tags
FROM latest_not_deleted_jobs t1
LEFT JOIN last_seen_job_timestamp t2 USING (workspace_id, job_id)
WHERE (t2.last_executed_at <= CURRENT_DATE() - INTERVAL 30 DAYS) OR (t2.last_executed_at IS NULL)
ORDER BY last_executed_at ASC
```

## 2. Job Reliability
To find the last completed run for a specific job:
```sql
SELECT
  workspace_id,
  job_id,
  run_id,
  period_start_time,
  period_end_time,
  result_state,
  termination_code,
  run_duration_seconds
FROM system.lakeflow.job_run_timeline
WHERE job_id = :job_id
  AND period_start_time > CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
ORDER BY period_start_time DESC
LIMIT 1
```
*Note: Ensure you check `result_state` for `SUCCEEDED`, `FAILED`, or `TIMED_OUT`.*

## 3. Data Lineage (`system.access.table_lineage`)
To trace the upstream dependencies of a Delta Table. Remember, if a table is external, its `source_table_full_name` might be NULL, so you must also check the `source_path`.

**Query: Find the exact job that produced a specific table:**
```sql
SELECT
  tl.source_table_full_name,
  tl.target_table_full_name,
  tl.entity_metadata.job_info.job_id AS producing_job_id,
  jrt.result_state,
  jrt.period_end_time AS last_run_completed_at
FROM system.access.table_lineage tl
LEFT JOIN system.lakeflow.job_run_timeline jrt
  ON tl.entity_metadata.job_info.job_id = jrt.job_id
  AND tl.entity_metadata.job_info.job_run_id = jrt.run_id
WHERE tl.target_table_full_name = "catalog.schema.your_table"
  AND tl.direct_access = true
ORDER BY jrt.period_end_time DESC
```

**PySpark Fallback (Handles Path-based External Tables):**
```python
def getLineageForTable(table_name):
    table_path = spark.sql(f"describe detail {table_name}").select("location").head()[0]
    df = spark.read.table("system.access.table_lineage")
    return df.where(
        (df.source_table_full_name == table_name)
        | (df.target_table_full_name == table_name)
        | (df.source_path == table_path)
        | (df.target_path == table_path)
    )

display(getLineageForTable("catalog.schema.your_table"))
```
