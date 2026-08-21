# Office Project Integration Guide: Email Ingestion Framework

A practical guide for integrating `msgraph_email_core` and `ar_collections_pipeline` into your Databricks workspace repository.

---

## 1. Files to Copy

From the `email-ingestion-framework` (or `ai-agents`) repository, copy these items into your office repository:

| Item | Source Location | Target Location in Office Repo | Purpose |
|---|---|---|---|
| **Generic Core** | `src/msgraph_email_core/` | `src/utils/msgraph_email_core/` | Microsoft Graph API sync connection, incremental delta tracking, attachment downloads, filtering, HTML table extraction |
| **AR Extension** | `src/ar_collections_pipeline/` | `src/utils/ar_collections_pipeline/` | Partner matrix & key-value parsing strategies, Japanese currency formatters (`¥`, `\`, `△`, `▲`), `CollectionRecord` output model |
| **Parsing Config** | `configs/customer_parsing_rules.yaml` | `configs/customer_parsing_rules.yaml` | Declarative parsing rules for partner email formats |

---

## 2. Target Directory Structure in Office Repo

```text
your-office-repo/
├── configs/
│   └── customer_parsing_rules.yaml        <-- 📄 Partner parsing configurations
│
├── notebooks/
│   └── ingest_ar_collections.py           <-- 🚀 Databricks pipeline notebook
│
└── src/
    └── utils/
        ├── email_utility.py               <-- (Existing email sender utility)
        ├── file_server_utils.py           <-- (Existing network drive utility)
        │
        ├── msgraph_email_core/            <-- 🌟 [NEW] Generic Core Package
        │   ├── __init__.py
        │   ├── models.py                  <-- EmailMessage, AttachmentItem
        │   ├── client.py                  <-- MSGraphEmailClient (pure sync requests)
        │   ├── filters.py                 <-- EmailFilter (chainable)
        │   └── html_tools.py              <-- HTMLTableExtractor
        │
        └── ar_collections_pipeline/       <-- 🏢 [NEW] AR Pipeline Extension
            ├── __init__.py
            ├── models.py                  <-- CollectionRecord
            ├── formatters.py              <-- JapaneseCurrencyCleaner
            └── yaml_mapper.py             <-- YamlMappingParser (4 strategies)
```

---

## 3. Required Python Dependencies

Install the lightweight standard packages in your Databricks cluster or notebook:

```python
%pip install requests pandas beautifulsoup4 lxml pyyaml
```

*(No `msgraph-sdk` or `nest_asyncio` required — the client uses pure synchronous `requests` calls).*

---

## 4. End-to-End Databricks Pipeline Notebook

Place this in your Databricks ingestion notebook (e.g. `notebooks/ingest_ar_collections.py`):

```python
# Databricks notebook source

# COMMAND ----------
# DBTITLE 1, 1. Install Dependencies
%pip install requests pandas beautifulsoup4 lxml pyyaml

# COMMAND ----------
# DBTITLE 1, 2. Import Libraries
import os
import yaml
from datetime import datetime, timezone
from pyspark.sql import functions as F

from src.utils.msgraph_email_core import MSGraphEmailClient, EmailFilter
from src.utils.ar_collections_pipeline import YamlMappingParser

# COMMAND ----------
# DBTITLE 1, 3. Load Secrets and Configuration
# Resolve Azure AD credentials from Databricks Secrets
SECRET_SCOPE  = "azure_scope"
tenant_id     = dbutils.secrets.get(scope=SECRET_SCOPE, key="tenant_id")
client_id     = dbutils.secrets.get(scope=SECRET_SCOPE, key="client_id")
client_secret = dbutils.secrets.get(scope=SECRET_SCOPE, key="client_secret")

# Target mailbox address
MAILBOX = "svc_global_bi@company.com"

# Target Delta table
TARGET_DELTA_TABLE = "main.finance.ar_collections_bronze"
STATE_DELTA_TABLE  = "main.finance.ar_ingestion_state"

# Load customer parsing rules YAML
yaml_path = "/Workspace/Repos/your_repo/configs/customer_parsing_rules.yaml"
with open(yaml_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

parser = YamlMappingParser(config.get("customers", {}))

# COMMAND ----------
# DBTITLE 1, 4. Fetch Incremental Delta State
saved_delta_token = None
try:
    if spark.catalog.tableExists(STATE_DELTA_TABLE):
        state_df = spark.sql(f"SELECT delta_token FROM {STATE_DELTA_TABLE} WHERE pipeline = 'ar_collections' ORDER BY updated_at DESC LIMIT 1")
        if not state_df.isEmpty():
            saved_delta_token = state_df.collect()[0]["delta_token"]
            print(f"Loaded saved delta token: {saved_delta_token[:30]}...")
except Exception as e:
    print(f"No previous state found, performing initial run: {e}")

# COMMAND ----------
# DBTITLE 1, 5. Ingest and Filter Emails
with MSGraphEmailClient(tenant_id, client_id, client_secret, MAILBOX) as client:
    # 1. Incremental fetch: only returns new/modified messages since previous run
    emails, new_delta_token = client.get_emails_incremental(folder="Inbox", delta_token=saved_delta_token)

print(f"Retrieved {len(emails)} new/updated email(s).")

# 2. Filter target emails (optional chainable filtering)
target_emails = (
    EmailFilter(emails)
    .by_has_attachments(False) # or filter by subject keywords
    .results()
)

# COMMAND ----------
# DBTITLE 1, 6. Parse and Map Emails to Collection Records
# YAML-driven parser maps unstructured tables to CollectionRecord objects
records = parser.parse_batch(target_emails)
print(f"Extracted {len(records)} collection record(s).")

# COMMAND ----------
# DBTITLE 1, 7. Write Extracted Data to Delta Lake
if records:
    records_dict = [r.to_dict() for r in records]
    df = spark.createDataFrame(records_dict)
    
    # Add audit timestamp
    df = df.withColumn("ingested_at", F.current_timestamp())
    
    # Append to Delta Lake Bronze table
    df.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(TARGET_DELTA_TABLE)
    display(df)
else:
    print("No records extracted.")

# COMMAND ----------
# DBTITLE 1, 8. Update Incremental State Token
if new_delta_token:
    state_record = [{
        "pipeline": "ar_collections",
        "delta_token": new_delta_token,
        "emails_processed": len(target_emails),
        "records_extracted": len(records),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }]
    state_df = spark.createDataFrame(state_record)
    state_df.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(STATE_DELTA_TABLE)
    print("Saved updated delta state token.")
```

---

## 5. Adding New Partner Formats in YAML

When a new customer/partner sends an email in a different layout, you **do not need to modify any Python code**. Simply add a new entry to `configs/customer_parsing_rules.yaml`:

```yaml
customers:
  NewPartnerName:
    match:
      subject_regex: '.*(NewPartner|PartnerKeyword).*'
      sender_email: null  # Optional sender filter
    strategy: vertical_key_value  # Choose 1 of 4 strategies
    code_source:
      table_index: 0
      target_regex: '請求先コード'
    amount_source:
      table_index: 0
      target_regex: '.*(支払額|入金額).*'
```

### Supported Layout Strategies:

1. **`vertical_key_value`** (e.g. KamoShoji, Chiyoda, Zett)
   - Code & amount are in key-value label/value pairs. Yields 1 record per email.
2. **`zip_columns_across_tables`** (e.g. Mega)
   - Billing codes span columns in Table 0, amounts span columns in Table 1. Yields N records.
3. **`zip_headers_to_row`** (e.g. Himaraya, Step, Amazon)
   - Billing codes are column headers of the target table; amounts are located in a matched row. Yields N records.
4. **`zip_rows_in_same_table`** (e.g. Imoto)
   - Code row and amount row exist within the same table. Yields N records.

---

## 6. Currency Cleaning & Japanese Formatting

The `JapaneseCurrencyCleaner` automatically handles all variations in email amounts:
- Standard Yen: `¥1,234,567` $\rightarrow$ `1234567.0`
- Full-width Yen: `￥144,590,047` $\rightarrow$ `144590047.0`
- Backslash Yen Variant: `\397,375,664` $\rightarrow$ `397375664.0`
- Negative Triangle (Japanese accounting): `△25,226,790` or `▲1,000` $\rightarrow$ `-25226790.0`
- Negative Signs & Parentheses: `¥-500`, `-¥500`, `(1,234)` $\rightarrow$ `-500.0`, `-1234.0`
- Excel Errors & Nulls: `#DIV/0!`, `#N/A`, `-`, `""` $\rightarrow$ `None`
