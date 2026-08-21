# Email Ingestion & Extraction Framework: Brainstorming & Architecture Document

## 1. Executive Summary & Problem Context

Modern enterprise data operations frequently receive business-critical datasets via automated or manual emails (e.g., Microsoft Graph/Exchange, SAP/Power Automate notifications, partner data drops). 

Historically, data engineers create ad-hoc, brittle scripts for each email format. This leads to:
1. **Fragile Parsers:** Changes in subject lines or email body formatting break downstream ETL.
2. **Special Character/Prefix Bugs:** e.g., Resent/Correction indicators like `再 2026_31W_取り込み明細.csv` causing naive substring slicing (`[:4]`) to extract `'再 20'` instead of `'2026'`.
3. **Lack of Observability/Auditability:** As raised in operational reviews (*"how is the status for audit log ?"*), pipelines often fail silently without tracing which email IDs were processed, when, and how many rows were extracted.
4. **Code Duplication:** Every new email source requires writing, testing, and maintaining a separate notebook or ingestion pipeline.

**Objective:** Build a **generic, YAML template-driven Email Ingestion & Extraction Utility** that can be plugged into any Databricks notebook, PySpark pipeline, or Airflow DAG without writing custom Python code for each new email type.

---

## 2. High-Level Architectural Blueprint

```
                    ┌────────────────────────────────────────────────────────┐
                    │               Microsoft Graph API (O365)               │
                    │               Endpoint: /users/{mailbox}/messages      │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                                                ▼
                    ┌────────────────────────────────────────────────────────┐
                    │                 Email Pipeline Engine                  │
                    │                                                        │
                    │  1. Secret Resolution (Databricks dbutils / Env)       │
                    │  2. Incremental Watermarking / Filter Evaluation       │
                    │  3. Async Batch Ingestion (msgraph-sdk)                │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                                                ▼
 ┌───────────────────────────┐      ┌────────────────────────────────────────┐
 │   YAML Pipeline Template  │ ───► │       Modular Extractor Subsystem      │
 │                           │      │                                        │
 │ • Matchers & Filters      │      │ • Text & Regex Matcher (Year/Week/Tag) │
 │ • Metadata Rules (Regex)  │      │ • HTML Table Parser (bs4 / pandas)     │
 │ • Table Column Mappings   │      │ • Attachment Streamer (ADLS / S3)      │
 │ • Audit & Sink Rules      │      │ • Column Renamer & Type Coercer        │
 └───────────────────────────┘      └───────────────────┬────────────────────┘
                                                        │
                                                        ▼
                    ┌────────────────────────────────────────────────────────┐
                    │                Standardized Output Layer               │
                    ├───────────────────────────┬────────────────────────────┤
                    │   Business Data (Delta)   │     Audit Logs (Delta)     │
                    │   • Extracted Table Rows  │     • Message ID & Sender  │
                    │   • Enriched Metadata     │     • Status & Timestamps  │
                    │   • Year, Week, Source    │     • Row Counts & Errors  │
                    └───────────────────────────┴────────────────────────────┘
```

---

## 3. Core Technical Components

### 3.1. Secret Resolution & Authentication
* Supports dynamic secret scopes in Databricks (`dbutils.secrets.get(scope, key)`) with fallback to environment variables for local testing.
* Uses Azure AD App Registration Service Principal with asynchronous `ClientSecretCredential`.

### 3.2. Regex & Metadata Extraction Layer
Solves variable-prefix edge cases using named regular expression groups:
* **Subject / Body Pattern:** `(?:再\s*)?(?P<year>\d{4})_(?P<week>\d{1,2}W)_(?P<report_name>[^\s.]+)`
* **Handling:**
  * `再 2026_31W_取り込み明細.csv` $\rightarrow$ `{'year': 2026, 'week': '31W', 'report_name': '取り込み明細'}`
  * `2026_31W_取り込み明細.csv` $\rightarrow$ `{'year': 2026, 'week': '31W', 'report_name': '取り込み明細'}`

### 3.3. HTML Table Extraction Engine
* Parses raw email HTML body using `BeautifulSoup` and `pandas.read_html`.
* Filters out layout/spacer tables created by Outlook / Exchange formatting.
* Applies declarative column renaming and type casting specified in the YAML template.
* Injects lineage metadata (`email_message_id`, `email_received_at`, `extracted_year`, `extracted_week`, `table_index`) into every extracted row.

### 3.4. Audit Logging & Compliance Layer
Every pipeline run generates audit records saved directly into an append-only Delta table:
* `message_id`: Unique Microsoft Graph message ID (prevents duplicate processing).
* `conversation_id`: Thread ID for grouping related messages.
* `received_at`: Email arrival timestamp (UTC / JST).
* `processed_at`: Ingestion execution timestamp.
* `status`: `SUCCESS`, `NO_TABLE_FOUND`, `SCHEMA_MISMATCH`, or `FAILED`.
* `rows_extracted`: Count of parsed table records.
* `error_message`: Full stacktrace / error details if parsing encountered issues.

---

## 4. Requirements Gathering Framework (Questions for Business & Product Teams)

When onboarding any new email data source, the Data Engineering team uses this structured questionnaire:

### A. Source & Access
1. **Target Mailbox:** What is the mailbox address (e.g., `svc_global_bi@adidas.com`)? Is it a User or Shared Mailbox?
2. **Access Method:** Do we have Service Principal access via Azure AD App Registration with `Mail.Read` application permissions?
3. **Mailbox Lifecycle:** Should processed emails remain unread, be marked as read (`isRead=true`), or be moved to an archive folder?

### B. Routing & Filter Criteria
4. **Sender Whitelist:** Which sender addresses or domains are authorized (e.g., `noreply@adidas.com`, `PowerAutomateNoReply@microsoft.com`)?
5. **Subject Line Rules:** What subject keywords or regex patterns uniquely identify this data stream?
6. **Volume & Schedule:** How often do emails arrive (e.g., daily 08:00 AM JST, weekly, or event-driven), and what is the expected email volume?

### C. Payload & Schema Specifications
7. **Source of Truth:** Is data contained within the **Email Body HTML Table**, **Key-Value Body Text**, or an **Attachment** (`.csv`, `.xlsx`, `.pdf`)?
8. **Metadata Tokens:** What metadata must be extracted from the subject/body (e.g., `Year`, `Week Number (31W)`, `Batch ID`, `Store ID`)?
9. **Table Schema:** What are the expected table headers, required columns, and data types?
10. **Schema Drift Policy:** If an unexpected column appears or an optional column is missing, should the pipeline fail or log a warning and proceed?

### D. Business Logic & Transformations
11. **Timezone Policy:** What is the standard business timezone (`UTC`, `JST / Asia/Tokyo`, `CET`)?
12. **Resend & Correction Policy:** When an email with a `再 ` (Resend) prefix arrives for an already processed `Year/Week`, should it **overwrite** existing data or **append with a version increment**?
13. **Language & Character Encoding:** Are there Japanese multi-byte characters, full-width numbers, or Katakana/Kanji normalization requirements?

### E. Destination & Observability
14. **Target Destination:** What is the target Delta Lake table name (e.g., `sadp_jpdna_dev.email_extracted_tables`)?
15. **Partitioning Strategy:** How should the Delta table be partitioned (`year`, `week`, `ingestion_date`)?
16. **Alerting Channel:** If an extraction fails, which MS Teams / Slack channel or email alert list should receive the failure notification?

---

## 5. End-to-End Pipeline Execution Flow

```
[ Scheduled Trigger / Databricks Job ]
                  │
                  ▼
[ Load YAML Template (e.g. jp_dna_intake.yaml) ]
                  │
                  ▼
[ Authenticate with MS Graph via Azure Identity ]
                  │
                  ▼
[ Query Unprocessed Emails (Filter by Subject/Sender) ]
                  │
                  ▼
[ For Each Email in Batch ]
    ├── 1. Extract Metadata via Regex (Year, Week, Report)
    ├── 2. Parse HTML Body for <table> Elements
    ├── 3. Clean & Rename Columns per YAML Mapping
    ├── 4. Tag Extracted Rows with Email Metadata & Lineage
    └── 5. Generate Audit Record (Status, Row Count, Timestamp)
                  │
                  ▼
[ Write Extracted Rows to Data Delta Table (Append / Merge) ]
                  │
                  ▼
[ Write Audit Records to Audit Delta Table (Append) ]
```

---

## 6. Open Discussion Topics & Next Steps

1. **Incremental State / Watermarking:**
   * Evaluate Delta Table Watermarking vs Graph API Delta Query (`/messages/delta`) for keeping track of last processed timestamp.
2. **Schema Evolution:**
   * Support Delta Lake's `mergeSchema=true` for non-breaking changes vs strict Pydantic validation for regulated financial data.
3. **Attachment Downloader Integration:**
   * Expand the engine to automatically stream attachments (`.xlsx`, `.csv`) directly to ADLS Gen2 landing zones.
4. **CI/CD & Template Management:**
   * Store YAML templates in a central repository or Unity Catalog volume so non-engineers / business analysts can update column mappings without code deployments.
