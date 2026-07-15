# DAVIS Reconciliation Examples

## Creator Log
- Creator: Biswajit Brahmma
- Artifact: DAVIS Reconciliation Examples
- Purpose: Behavioral examples for the DAVIS reconciliation skill

## Example 1: User provides everything up front
User input:
- target_table: lakehouse.cadp_jpdna_pool_lh.vw_jp_dtc_md_demand
- source_table: lakehouse.cadp_dtc_sellout_lh.ecom_sor_vw
- kpis: net_quantity, net_val_of_billing_item
- key_cols: posting_date, channel

Expected behavior:
- Use the supplied information as guidance.
- Still execute State 1 through State 6 sequentially.
- Do not skip target profiling, grain validation, lineage review, or source validation.
- Do not produce the final full reconciliation framework unless explicitly requested.

## Example 2: Lineage finds additional business rules
Scenario:
Lineage search finds additional logic in a notebook, such as:
- partner exclusions
- tax adjustments
- article exclusions
- phase-out filters

Expected behavior:
- Summarize them under "Additional rules found but NOT yet applied"
- Ask the user which of those rules should be incorporated
- Do not merge them automatically into `source_agg`

## Example 3: Successful validation checkpoint
Expected validation output after State 5:
- a compact result table comparing `source_agg` and `target_agg`
- row-level or KPI-level visible proof
- clear numeric deltas
- explicit approval gate before moving to final CTE delivery

## Example 4: Final delivery
Expected output in State 6:
- one SQL block for `target_agg`
- one SQL block for `target_refresh`
- one SQL block for `source_agg`
- one SQL block for `source_refresh`

## Example 5: Guardrail returns zero rows
Scenario:
The selected anchor date has not yet been loaded in the target or source table. Common causes include:
- The anchor date is today and the pipeline has not yet completed its daily load.
- The anchor date falls before the data floor date (e.g., before `2024-11-01` for a source with a hard floor filter).
- The target view has not refreshed for the selected date due to upstream lag.

Expected behavior:
- Stop the workflow immediately.
- Explain the likely cause based on the context (unloaded date, floor boundary, or refresh lag).
- Offer to rerun using the previous fully loaded business date.
- Do not proceed to the next state or claim validation on empty evidence.

## Example 6: Lineage evidence with traceback references
Scenario:
The agent finds source logic across notebook cells, job tasks, and query history during lineage tracing.

Expected behavior:
- Present a compact lineage evidence table.
- For each recovered rule, show source type, workspace path or job name, cell/query/task reference, and the exact logic found.
- Clearly mark whether each rule was applied now, left pending approval, or rejected.

## Example 7: All lineage fallbacks exhausted
Scenario:
UC system lineage (`system.access.table_lineage`) is inaccessible. `readTable` topQueries, `querySearch`, and `searchAssets` all return no relevant results for the target or source table.

Expected behavior:
- State explicitly that all 3 fallback levels were attempted and none returned usable lineage evidence.
- Do not guess at source logic or proceed with an unverified assumption.
- Ask the user to supply the source transformation logic manually before proceeding — including source table, key columns, KPIs, filters, joins, and any known business rules.
- Do not advance to State 5 until the user has provided or confirmed the source logic.

## Example 8: Lineage finds archived or duplicated scripts
Scenario:
During lineage tracing (State 4A), the agent searches the workspace and finds multiple notebooks referencing the target table, such as:
- `/Workspace/cadp-jpdna/notebooks/archive/old_recon_v1`
- `/Workspace/cadp-jpdna/notebooks/gold/whs_sellout/prod_recon`

Expected behavior:
- Do not assume the newer or older script is the correct one.
- Present both scripts in the State 4A Lineage References table.
- Explicitly ask the user to clarify which script is the active production source before moving to State 4B.
- If the user identifies one as an archive, discard its logic entirely and do not include it in the proposed rules.
