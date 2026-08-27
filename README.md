# 📬 mail2delta

**mail2delta** is an enterprise-grade, deterministic email ingestion and financial reconciliation framework that streams unstructured emails from **Microsoft 365 (MS Graph API)** directly into **Databricks Delta Lake**.

Built from first principles: **Zero-LLM dependency**, **100% deterministic rule-based parsing**, **YAML-driven configuration**, and **idempotent composite-key MERGE upserts**.

---

## 🏗️ Architecture

The framework is structured into 4 decoupled layers:

```text
mail2delta/
├── configs/
│   └── customers.yaml              # Layer 1: Declarative rules & custom merge_keys
│
├── src/
│   ├── core/                       # Layer 2: Universal I/O & string cleaners
│   │   ├── ms_graph_client.py      # OAuth2 Entra ID Client & OData fetcher
│   │   ├── delta_sink.py           # Delta Lake Idempotent Upsert Engine
│   │   ├── html_parser.py          # HTML-to-text & table normalization
│   │   └── currency_cleaner.py     # Global currency (¥, $, €, △, ▲) sanitizer
│   │
│   ├── strategies/                 # Layer 3: Pluggable extraction strategies
│   │   ├── base_strategy.py        # Interface contract (extract(email, params))
│   │   └── key_value_strategy.py   # Deterministic key-value & table row parser
│   │
│   └── router/                     # Layer 4: Dispatcher
│       └── strategy_router.py      # Matches subject to customer & dispatches strategy
│
└── notebooks/                      # Orchestrator (Databricks Serverless Job)
    └── finance_ops_collections.py  # High-Watermark + Gate 1 + Router + Gate 2
```

---

## 🛡️ Key Features

* **Hybrid High-Watermark & Two-Gate Deduplication:**
  * **Gate 1 (Driver / Network Filter):** Calculates the high watermark with a 7-day safety buffer. Skips known `email_unique_id`s in memory before parsing.
  * **Gate 2 (Delta Lake MERGE):** Dynamically constructs an idempotent `MERGE INTO` statement using business composite keys (`customer_code`, `payment_due_label`) defined in YAML. Automatically overwrites corrections without creating duplicates.
* **Global Currency & Accounting Support:**
  * Cleanly handles Japanese Yen (`¥`, `￥`, `円`), USD (`$`), Euro (`€`), British Pound (`£`).
  * Handles accounting negatives like `(1,000)`, `△500,000`, `▲1,234,567`, and `-500`.
* **Zero-Code Customer Onboarding:**
  * Supporting a new partner or email format requires only adding a YAML block in `configs/customers.yaml`.

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
