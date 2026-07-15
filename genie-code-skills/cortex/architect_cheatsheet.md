# 🧠 Cortex — Architect Cheatsheet

This is your persistent knowledge base. Read this before designing any new system, agent, or pipeline in the Databricks ecosystem.

---

## 1. The Agent Ecosystem Map

| Agent | Trigger Phrase | Primary Output |
|-------|---------------|----------------|
| `cortex` | "I want to build...", "Help me design...", "Let's brainstorm..." | Architectural plans, new SKILL.md files, prompts |
| `job-profiling-agent` | "Profile job X", "Why is job Y slow?" | FinOps + Spark performance report |
| `eda-dashboard-builder` | "Analyze table X", "Build a KPI dashboard" | PySpark EDA results + AI/BI Dashboard SQL |
| `infra-dashboard-builder` | "Monitor compute costs", "Build an observability dashboard" | system table SQL + Dashboard widgets |
| `skill-refiner` | "The agent made a mistake", "Update the skill" | Updated SKILL.md or cheatsheet diff |
| `davis-recon-builder` | "Build a recon query for source X to target Y" | Validated source_agg, target_agg CTEs |
| `davis-recon-query-builder` | "Generate the final recon framework" | Full OUTER JOIN reconciliation SQL |

---

## 2. The SKILL.md Template (For New Agents)

When the user asks to create a new agent, always use this exact structure:

```markdown
---
name: <kebab-case-name>
description: Use this skill when <exact trigger condition>. 
---

# 🎯 <Agent Display Name>

## Karpathy Core Principles (Mandatory)
1. **Think Before Coding:** ...
2. **Simplicity First:** ...
3. **Surgical Changes:** ...
4. **Goal-Driven Execution:** ...

## Role & Persona
You are a <persona>. Your primary directive is to <mission>.

## The Agentic Protocol (Plan & Solve)

### 1. Goal Setting & Planning (The Brain)
- **Knowledge Reference:** Before generating any code, read `<name>_cheatsheet.md`.
- Do NOT write code immediately.
- Draft a plan using verifiable goals:
  `1. [Step] → verify: [check]`
- **PAUSE AND WAIT** for user approval.

### 2. Execution (The Hands)
- ...

### 3. Reflection & Self-Correction (The ReAct Loop)
- If execution fails, analyze the error, self-correct, and retry.

### 4. Synthesis & Deliverables
- ...

## Strict Constraints
- ...
```

---

## 3. Databricks Architecture Decision Patterns

### When to use a Job vs. a DLT Pipeline
| Scenario | Recommendation |
|----------|---------------|
| Simple ETL, batch, scheduled | **Databricks Job** (cheaper, simpler) |
| Streaming + CDC + auto-retries | **Delta Live Tables** (more complex, self-healing) |
| Complex multi-task orchestration | **Databricks Job with task dependencies** |

### When to use a Genie Space vs. an AI/BI Dashboard
| Scenario | Recommendation |
|----------|---------------|
| Business user asking ad-hoc natural language questions | **Genie Space** |
| Fixed KPI monitoring with known metrics | **AI/BI Dashboard** |
| Combination of both | **Genie Space + pinned Dashboard** |

### Unity Catalog Layer Design (Medallion)
```
Bronze (raw)  → exact copy of source, append-only, no transformations
Silver (clean) → validated, typed, deduplicated, business-key joined
Gold (serving) → aggregated, metric-ready, optimized for BI tools
```

---

## 4. Key Databricks System Tables (For Observability Agents)

| Table | What it contains |
|-------|-----------------|
| `system.lakeflow.jobs` | All job definitions (SCD2 — dedup with ROW_NUMBER) |
| `system.lakeflow.job_run_timeline` | Every run with state, duration, retries |
| `system.lakeflow.job_task_run_timeline` | Per-task durations within a run |
| `system.billing.usage` | DBU consumption per workspace/job |
| `system.compute.clusters` | Cluster configs: node type, autoscale min/max |
| `system.access.table_lineage` | Upstream/downstream table dependencies |
| `system.query.history` | Every SQL/Python query: duration, spill, bytes read |

**Critical dedup pattern for `system.lakeflow.jobs` (SCD2):**
```sql
SELECT * FROM system.lakeflow.jobs
QUALIFY ROW_NUMBER() OVER (PARTITION BY workspace_id, job_id ORDER BY change_time DESC) = 1
AND delete_time IS NULL
```

---

## 5. Karpathy Verifiable Goal Format

Always format execution plans like this — never use vague imperative steps:

```
✅ DO:
1. [Query system.lakeflow] → verify: [job run success rates successfully retrieved]
2. [Detect anomalous run] → verify: [run_id with highest execution_duration identified]

❌ DON'T:
1. Fetch runs
2. Find slow run
```

---

## 6. Common Databricks Anti-Patterns to Flag

| Anti-Pattern | Impact | Fix |
|-------------|--------|-----|
| Column-by-column PySpark loop | N Spark jobs instead of 1 | Single-pass `agg()` with all expressions |
| `countDistinct()` on large tables | Expensive exact count | `approx_count_distinct(col, rsd=0.01)` |
| `dbutils.notebook.entry_point.getDbutils().notebook().getContext().tags()` | Fails in USER_ISOLATION mode | Use `WorkspaceClient().config.host` from SDK |
| Hardcoded Databricks host/token | Security vulnerability | `ctx.apiToken().get()` + `ctx.tags().get("browserHostName")` |
| No dedup on system.lakeflow.jobs | Returns duplicate job definitions | Always use `QUALIFY ROW_NUMBER()` pattern |

---

## 7. Decisions Log

*Cortex maintains an evolving record of all major architectural decisions made with the user.*

| Date | Decision | Rationale | Tradeoffs Accepted |
|------|----------|-----------|-------------------|
| 2026-07-15 | Adopted Karpathy "Plan & Solve" ReAct loop as standard OS for all agents | Prevents hallucination, forces verification before execution | Slightly slower initial response (plan approval required) |
| 2026-07-15 | Used `approx_count_distinct` over `countDistinct` in EDA agent | 10-100x faster on large Delta tables, 1% error tolerance acceptable for EDA | Exact distinct counts not available without `ANALYZE TABLE` |
| 2026-07-15 | Adopted `ctx.apiToken().get()` pattern over hardcoded tokens | Air-gapped enterprise security — no DLP violations | Token expires with notebook session |
| 2026-07-15 | job_profiling_agent uses SDK task metrics as fallback when Spark UI unavailable | Terminated clusters have no live Spark UI proxy | SDK metrics are less granular than raw Spark stage metrics |
