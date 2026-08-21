# 🤖 Databricks Autonomous AI Agents (Karpathy OS)

A suite of enterprise-grade, fully autonomous AI Agents and Data Engineering Utilities designed specifically for the Databricks Workspace Assistant and modern Lakehouse pipelines. These tools operate using the `.assistant/skills/` directory structure and modular Python packages.

## 🏗️ The Architecture (Karpathy Principles)

All agents and utilities in this repository are built on a strict **Plan-and-Solve (ReAct)** architecture heavily inspired by Andrej Karpathy's LLM coding principles:

1. **Think Before Coding:** Agents explicitly state assumptions and ask for clarification before generating code.
2. **Simplicity First:** Agents and utilities write the minimum code necessary, avoiding bloated abstractions.
3. **Surgical Changes:** Modify only what is necessary and clean up transient scratch files.
4. **Goal-Driven Execution:** Dynamic execution graphs with verifiable success criteria and automated quality gates.

---

## 👥 The Agent Roster

This repository contains specialized Databricks Agents and Data Utilities:

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

### 5. `msgraph_email_core` & `ar_collections_pipeline` (Email Ingestion Framework)
*   **Role:** Platform-agnostic MS Graph email ingestion and declarative parsing utility.
*   **Capabilities:** Pure synchronous, requests-based client with delta token query support, chainable email filtering, robust HTML table extraction into DataFrames, and YAML-driven partner matrix parsing.

---

## 🚀 How to Deploy in Databricks

1. Open your Databricks Workspace.
2. Navigate to your user directory: `Workspace > Users > [Your Email]`.
3. Create a folder named `.assistant/skills/` if it does not already exist.
4. Clone or copy the contents of the `genie-code-skills/` directory from this repository directly into `.assistant/skills/`.
5. Open the Databricks Assistant panel and invoke an agent using `@` (e.g., `@eda-dashboard-builder`).
