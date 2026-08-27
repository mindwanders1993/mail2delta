# 📬 mail2delta

**mail2delta** is an enterprise-grade, deterministic email ingestion and financial reconciliation framework that streams unstructured emails from **Microsoft 365 (MS Graph API)** directly into **Databricks Delta Lake**.

Built from first principles with a strictly decoupled 3-tier architecture: **Connectors (Input)**, **Transformers (Extraction & Rules)**, and **Sinks (Storage)**.

---

## 🏗️ Decoupled Architecture

```text
mail2delta/
├── configs/
│   └── customers.yaml              # Declarative rules & customer merge_keys
│
├── src/
│   ├── connectors/                 # 1. CORE I/O (SOURCE) & TOOLS
│   │   ├── ms_graph_client.py      # OAuth2 Entra ID Client & OData fetcher
│   │   └── html_parser.py          # HTML-to-text & table DOM parser
│   │
│   ├── transformers/               # 2. DATA EXTRACTION & BUSINESS RULES
│   │   ├── base.py                 # Abstract strategy interface (BaseEmailStrategy)
│   │   ├── key_value_parser.py     # Deterministic key-value & table row parser
│   │   ├── currency_cleaner.py     # Global currency (¥, $, €, △, ▲) sanitizer
│   │   └── strategy_router.py      # Declarative YAML router & dispatcher
│   │
│   └── sinks/                      # 3. DATA WRITE & STORAGE (SINK)
│       └── delta_sink.py           # Dynamic composite-key Delta Lake MERGE writer
│
└── notebooks/                      # 4. DATABRICKS JOB ORCHESTRATOR
    └── finance_ops_collections.py  # Connectors -> Transformers -> Sinks
```

---

## 🛡️ Key Features

* **Strict Domain Isolation:**
  * **Connectors:** Only knows Microsoft Graph API and DOM parsing. Zero knowledge of business logic or database schemas.
  * **Transformers:** Only knows regex rules, customer configurations, and currency cleaning. Zero knowledge of network protocols or Spark.
  * **Sinks:** Only knows Delta Lake `MERGE INTO` SQL and composite keys. Zero knowledge of source protocols or customer emails.
* **Hybrid High-Watermark & Two-Gate Deduplication:**
  * **Gate 1 (Driver / Network Filter):** Calculates high watermark with a 7-day safety buffer. Skips known `email_unique_id`s in memory before parsing.
  * **Gate 2 (Delta Lake MERGE):** Dynamically constructs an idempotent `MERGE INTO` statement using business composite keys (`customer_code`, `payment_due_label`) defined in YAML. Automatically overwrites corrections without creating duplicates.
* **Global Currency & Accounting Support:**
  * Handles Japanese Yen (`¥`, `￥`, `円`), USD (`$`), Euro (`€`), British Pound (`£`).
  * Handles accounting negatives like `(1,000)`, `△500,000`, `▲1,234,567`, and `-500`.

---

## ⚙️ Declarative Configuration (`configs/customers.yaml`)

```yaml
customers:
  KamoShoji:
    subject_regex: "KamoShoji|加茂商事"
    strategy: "key_value_table"
    merge_keys:
      - "customer_code"
      - "payment_due_label"
    params:
      code_regex: "請求先コード"
      amount_regex: "支払額"
      currency: "JPY"
      default_label: "3/31 支払額"
```

---

## 🚀 Databricks Deployment

1. In Databricks Workspace, go to **Workspace** ➔ **Users** ➔ `[Your Username]`.
2. Click **Create** ➔ **Git folder**.
3. Enter repository URL: `https://github.com/mindwanders1993/mail2delta.git`.
4. Open and run [`notebooks/finance_ops_collections.py`](file:///Users/mrrobot/Desktop/Projects/email-ingestion-framework/notebooks/finance_ops_collections.py).

---

## 🧪 Running Unit Tests

```bash
PYTHONPATH=src pytest tests/
```
