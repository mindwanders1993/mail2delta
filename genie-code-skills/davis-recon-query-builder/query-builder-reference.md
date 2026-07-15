# DAVIS Recon Query Builder Reference

## Creator Log
- Creator: Biswajit Brahmma
- Artifact: DAVIS Recon Query Builder Reference
- Purpose: Defines the exact boilerplate output structure for the reconciliation query to match the downstream ingestion table schema.

## Core Architecture
The final reconciliation query MUST follow this exact CTE sequence. Do not invent new structures. The final schema is strictly validated by the ingestion pipeline.

1. **User Provided CTEs:**
   - `source_agg`
   - `target_agg`
   - `source_refresh`
   - `target_refresh`

2. **Unpivot CTEs (`source_kpis` & `target_kpis`):**
   - Transforms the metric columns into two columns: `kpis` (the metric name) and `value`.
   - You may use sequential `UNION ALL` statements (as seen in the examples) or Spark's `stack()` function, but the resulting columns must be the grain columns plus `kpis` and `value`.

3. **Reconciliation Base CTE (`reconciliation_base`):**
   - A `FULL OUTER JOIN` between `source_kpis` and `target_kpis` on the grain columns and `kpis`.
   - `CROSS JOIN` with `source_refresh` and `target_refresh`.
   - Calculates `absolute_diff = NVL(t.value, 0) - NVL(s.value, 0)`.
   - Calculates `diff_percentage` safely (handling division by zero).
   - Calculates `status` ('MATCH', 'WITHIN_THRESHOLD', 'DISCREPANCY').
   - Calculates `target_up_to_date_flag` (comparing refresh times).
   - Adds `reconciliation_time` (using `from_utc_timestamp(current_timestamp(), 'Asia/Tokyo')`).

4. **Final Output (The strict schema):**
   - The final `SELECT` must strictly map to the exact ingestion table schema. It handles up to 3 grain columns dynamically:
     - `key_col1` (String literal of the 1st grain column name)
     - `key_col1_value` (The actual value of the 1st grain column)
     - `key_col2` (String literal of the 2nd grain column name, or 'NA' if there is no 2nd grain)
     - `key_col2_value` (The actual value of the 2nd grain column, or NULL if none)
     - `key_col3` (String literal of the 3rd grain column name, or 'NA' if there is no 3rd grain)
     - `key_col3_value` (The actual value of the 3rd grain column, or NULL if none)
     - `target_table` (String literal of target table name)
     - `source_table` (String literal of source table name)
     - `kpis`
     - `source_value`
     - `target_value`
     - `absolute_diff`
     - `diff_percentage`
     - `status`
     - `source_last_refresh_time`
     - `target_last_refresh_time`
     - `target_up_to_date_flag`
     - `reconciliation_time`

## Key Column Mapping Logic
You must dynamically map the user's grain columns into `key_col1`, `key_col2`, and `key_col3`. 
If the user only has 1 grain column (e.g., `tenjikai_season`), map it to `key_col1` and `key_col1_value`. Hardcode `'NA'` for `key_col2` and `key_col3`, and `NULL` for `key_col2_value` and `key_col3_value`.
