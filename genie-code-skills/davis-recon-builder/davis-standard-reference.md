# DAVIS Reconciliation Reference

## Creator Log
- Creator: Biswajit Brahmma
- Artifact: DAVIS Reconciliation Reference
- Purpose: Reference guidance for deterministic notebook-based reconciliation delivery

## Objective
The DAVIS reconciliation workflow is used to create a deterministic source-to-target reconciliation between a source-side simulated aggregation and a target-side delivered aggregation.

The primary deliverables are:
- `source_agg`
- `target_agg`
- `source_refresh`
- `target_refresh`

These 4 CTEs are intended to be plugged into a downstream internal reconciliation framework.

## Core principles

### 1. Grain-first validation
Always validate the raw reconciliation grain before finalizing aggregation logic.

### 2. Incremental drafting
Do not jump directly to the final reconciliation query. First validate:
- target profiling
- target grain
- `target_agg`
- source lineage
- `source_agg`
- refresh CTEs

### 3. No silent logic injection
If lineage research finds extra filters, exclusion logic, tax treatment, phase-out rules, or transformation rules, those must be proposed to the user before being incorporated.

### 4. Validation means visible proof
A CTE is considered validated only when:
- it executes successfully, and
- the agent presents rows, timestamps, or numeric comparison output to the user

## Standard CTE roles

### target_agg
Target-side aggregation at the approved grain and KPI list.

### source_agg
Source-side simulation of the target logic, based on lineage-confirmed transformations.

### target_refresh
Latest refresh or last-update indicator for the target dataset, using the same scoped filters where relevant.

### source_refresh
Latest refresh or last-modified indicator for the source dataset, using the same scoped filters where relevant.

## Guardrail convention
During exploration and validation, use a 1-day date guardrail unless the user requests a different validation window.

During final delivery, remove the guardrail but preserve the exact approved business logic.

## Validation output expectation
When validating `source_agg` against `target_agg`, present:
- approved grain columns
- KPI name
- source value
- target value
- delta
- optional delta percentage if helpful

## Lineage evidence expectation
When source-side logic is recovered through lineage tracing, the agent should document:
- where the logic was found
- what exact rule was recovered
- whether the rule was applied, rejected, or left pending user approval

Present findings as a compact lineage evidence table with columns: Source Type | Workspace Path / Job Name | Cell / Query / Task | Logic Recovered | Status (applied / pending / rejected).

Preferred references:
- workspace notebook path + cell number
- Databricks job name + task name
- query history source + query identifier
- UC lineage source when available

## Operational notes
- Validation should use a shared anchor business date for the full session. Do not re-evaluate `current_timestamp()` independently in each CTE.
- Partial-day discrepancies can occur when source and target refresh at different times within the same calendar day.
- If a validation guardrail returns 0 rows, prefer rerunning on the previous fully loaded date rather than continuing with empty evidence.

## Final delivery expectation
The default final output is the 4 approved CTEs only.

Do not include:
- unpivot logic
- full outer join assembly
- pass/fail framework
- templated reconciliation wrapper

unless the user explicitly asks for those later.
