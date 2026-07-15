# DAVIS Recon Query Builder Examples

## Creator Log
- Creator: Biswajit Brahmma
- Artifact: DAVIS Recon Query Builder Examples
- Purpose: Behavioral examples for the DAVIS Recon Query Builder agent

## Example 1: Missing CTEs
Scenario: The user pastes `source_agg` and `target_agg` but forgets the refresh CTEs.
Expected Behavior:
- Do not attempt to guess or write the refresh CTEs.
- Stop at State 1 and explicitly state: *"I see the aggregation CTEs, but I am missing `source_refresh` and `target_refresh`. Please provide them before we proceed."*

## Example 2: Threshold Pushback
Scenario: The user asks for a dynamic threshold based on historical volatility.
Expected Behavior:
- Adhere to the Simplicity First mandate.
- Push back gently: *"To maintain simplicity and determinism in the standard DAVIS framework, I recommend using hardcoded percentage or absolute thresholds (e.g., 1% variance). Shall we use 1%, or do you still want to proceed with the complex dynamic threshold?"*

## Example 3: The Final Query Structure (Strict Ingestion Schema)
The final query delivered in State 4 MUST look exactly like this template, strictly adhering to the `key_col` ingestion layout:

```sql
WITH 
-- 1. Source aggregated data (Provided by user)
source_agg AS (
    -- [User provided logic]
),

-- 2. Target aggregated data (Provided by user)
target_agg AS (
    -- [User provided logic]
),

-- 3. Source refresh time (Provided by user)
source_refresh AS (
    -- [User provided logic]
),

-- 4. Target refresh time (Provided by user)
target_refresh AS (
    -- [User provided logic]
),

-- 5. Source metrics unpivoted
source_kpis AS (
  SELECT tenjikai_season, 'quantity' AS kpis, quantity AS value FROM source_agg
  UNION ALL
  SELECT tenjikai_season, 'amount' AS kpis, amount AS value FROM source_agg
  UNION ALL
  SELECT tenjikai_season, 'std_cost' AS kpis, std_cost AS value FROM source_agg
),

-- 6. Target metrics unpivoted
target_kpis AS (
  SELECT tenjikai_season, 'quantity' AS kpis, quantity AS value FROM target_agg
  UNION ALL
  SELECT tenjikai_season, 'amount' AS kpis, amount AS value FROM target_agg
  UNION ALL
  SELECT tenjikai_season, 'std_cost' AS kpis, std_cost AS value FROM target_agg
),

-- 7. Final reconciliation results with difference calculations
reconciliation_base AS (
  SELECT
    COALESCE(s.tenjikai_season, t.tenjikai_season) AS tenjikai_season,
    'vw_jp_tenjikai_order_summary' AS target_table,
    'jp_tenjikai_order_fct' AS source_table,
    s.kpis,
    NVL(s.value, 0) AS source_value,
    NVL(t.value, 0) AS target_value,
    ROUND((NVL(t.value, 0) - NVL(s.value, 0)), 2) AS absolute_diff,
    CASE
      WHEN NVL(t.value, 0) = 0 AND NVL(s.value, 0) = 0 THEN '0%'
      WHEN NVL(t.value, 0) = 0 THEN NULL -- Avoid division by zero
      ELSE CONCAT(ROUND(((NVL(t.value, 0) - NVL(s.value, 0)) / NVL(t.value, 0)) * 100, 2), '%')
    END AS diff_percentage,
    CASE
      WHEN NVL(t.value, 0) = 0 AND NVL(s.value, 0) = 0 THEN 'MATCH'
      WHEN ABS(COALESCE(((NVL(t.value, 0) - NVL(s.value, 0)) / NULLIF(NVL(t.value, 0), 0)) * 100, 9999)) <= 0.0 THEN 'WITHIN_THRESHOLD'
      ELSE 'DISCREPANCY'
    END AS status,
    sr.source_last_refresh_time,
    tr.target_last_refresh_time,
    CASE
      WHEN sr.source_last_refresh_time IS NULL OR tr.target_last_refresh_time IS NULL THEN 'Unknown'
      WHEN tr.target_last_refresh_time >= sr.source_last_refresh_time THEN 'Yes'
      ELSE 'No'
    END AS target_up_to_date_flag,
    from_utc_timestamp(current_timestamp(), 'Asia/Tokyo') AS reconciliation_time
  FROM
    source_kpis s
      FULL OUTER JOIN target_kpis t
        ON COALESCE(s.tenjikai_season, 'NULL') = COALESCE(t.tenjikai_season, 'NULL')
        AND s.kpis = t.kpis
      CROSS JOIN source_refresh sr
      CROSS JOIN target_refresh tr
)

-- 8. Final Output (Strict Schema Mapping)
SELECT
  'tenjikai_season' AS key_col1,
  tenjikai_season AS key_col1_value,
  'NA' AS key_col2,
  NULL AS key_col2_value,
  'NA' AS key_col3,
  NULL AS key_col3_value,
  target_table,
  source_table,
  kpis,
  source_value,
  target_value,
  absolute_diff,
  diff_percentage,
  status,
  source_last_refresh_time,
  target_last_refresh_time,
  target_up_to_date_flag,
  reconciliation_time
FROM
  reconciliation_base
ORDER BY
  key_col1_value DESC,
  kpis;
```
