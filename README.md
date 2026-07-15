# 🤖 Databricks Autonomous AI Agents (Karpathy OS)

A suite of enterprise-grade, fully autonomous AI Agents designed specifically for the Databricks Workspace Assistant. These agents operate using the `.assistant/skills/` directory structure, allowing the native Databricks AI Assistant to inherit specialized domain knowledge.

## 🏗️ The Architecture (Karpathy Principles)

All agents in this repository are built on a strict **Plan-and-Solve (ReAct)** architecture heavily inspired by Andrej Karpathy's LLM coding principles:

1. **Think Before Coding:** Agents explicitly state assumptions and ask for clarification before generating PySpark or Databricks SQL.
2. **Simplicity First:** Agents are instructed to write the minimum code necessary, avoiding bloated abstractions.
3. **Surgical Changes:** When fixing code, agents modify only the failing lines and clean up their own mess.
4. **Goal-Driven Execution:** Agents draft dynamic execution graphs using verifiable success criteria (e.g., `1. [Analyze Nulls] -> verify: [null_count metrics successfully printed]`) before executing.

## 👥 The Agent Roster

This repository contains four specialized Databricks Agents:

### 1. `job_profiling_agent` (The FinOps Troubleshooter)
*   **Role:** Analyzes Databricks Job runs and Spark performance bottlenecks.
*   **Capabilities:** Queries the Databricks Python SDK and Spark REST API to diagnose slow runs, memory spills, and cluster setup latencies.

### 2. `infra_dashboard_builder` (The Platform Observability Dev)
*   **Role:** Builds AI/BI Dashboards for Job Monitoring and Infrastructure Health.
*   **Capabilities:** Generates optimized Databricks SQL queries against Unity Catalog System Tables (`system.lakeflow`, `system.compute`, `system.billing`).

### 3. `eda_dashboard_builder` (The Data Quality BI Dev)
*   **Role:** Performs Exploratory Data Analysis (EDA) and builds Business KPI Dashboards.
*   **Capabilities:** Generates highly optimized, single-pass PySpark profiling aggregations to detect nulls, skewness, and cardinality, then translates findings into Databricks AI/BI Dashboards.

### 4. `skill_refiner` (The Meta-Architect)
*   **Role:** A Self-Improving Meta-Agent that watches and upgrades the other three.
*   **Capabilities:** Analyzes chat history for failed code or user corrections, and autonomously rewrites the underlying `SKILL.md` or `cheatsheet.md` files of other agents to permanently fix failure patterns.

## 🚀 How to Deploy in Databricks

1. Open your Databricks Workspace.
2. Navigate to your user directory: `Workspace > Users > [Your Email]`.
3. Create a folder named `.assistant/skills/` if it does not already exist.
4. Clone or copy the contents of the `genie-code-skills/` directory from this repository directly into `.assistant/skills/`.
5. Open the Databricks Assistant panel and invoke an agent using `@` (e.g., `@eda-dashboard-builder`).
