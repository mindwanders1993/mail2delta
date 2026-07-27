# 📦 Wholesale Sellout (JP) Data Product

**Created by**: mindwanders1993 | **Last updated on**: [Date]

## 🛡️ Stewardship Hero Card
* **Data Owner**: [Owner/Team]
* **Freshness (SLA)**: [e.g., Daily 6:30 AM JST]
* **Grain**: [e.g., 1 row per Article per Season]
* **Sensitivity**: [e.g., High / Contains PII]

[ **Background** ] | [ **Entity Relationship Diagram (ERD)** ] | [ **Databricks** ] | [ **Power BI** ] | [ **ETLs** ] | [ **FAQ** ] | [ **Resources** ]

---

## Background
[Provide a brief overview of key sources and the business purpose of this dataset.]

The Wholesale Sellout pipeline processes raw sales files from various retail partners. 
* **Sources**: File Server, FTP
* **Formats**: `.xlsx`, `.xls`, `.csv`, `.tar`, `.txt`, `.zip`
* **Lookups**: Joins with Article Master and Store Master

---

## Entity Relationship Diagram (ERD)

```mermaid
flowchart LR
    %% Lineage based on table lineage and user input
    A1[FTP Server] -->|raw files (.csv, .xlsx)| B[(whs_sellout_audit_log)]
    A2[File Server] -->|raw files (.txt, .zip)| B
    B -->|Cleansing Job| C[(whs_sellout_s)]
    L1[(Article Master)] -.->|Lookup| C
    C -->|Aggregation Job| D[(jp_whs_sellout_g)]
    D -->|Semantic Layer| E[[jp_whs_sellout_report_vw]]
```

---

## Databricks (Table Catalog & Dictionaries)

| name | code | description | granularity | refresh schedule |
| :--- | :--- | :--- | :--- | :--- |
| **`whs_sellout_audit_log`** | [code_link] | Tracks file arrival, download timestamps, and bronze failure rates. | 1 row per file | continuous / streaming |
| **`whs_sellout_s`** | [code_link] | Cleansed, granular sellout data. | 1 row per transaction | daily 5:15AM JST |
| **`jp_whs_sellout_g`** | [code_link] | Aggregated metrics specifically for the Japan (JP) market. | 1 row per article per week | daily 6:30AM JST |
| **`jp_whs_sellout_report_vw`** | [code_link] | Semantic view used by Power BI. | 1 row per article per week | daily 6:30AM JST |

### Data Dictionaries & Profiling

<details>
<summary><b>Click to expand: <code>whs_sellout_audit_log</code> (Bronze/Audit)</b></summary>

| Column Name | Data Type | Description | Null % |
| :--- | :--- | :--- | :--- |
| `input_file_name` | `string` | Name of the raw file from FTP. | 0% |
| `bronze_status` | `string` | Success or Failed status of initial ingest. | 0% |

</details>

<details>
<summary><b>Click to expand: <code>whs_sellout_s</code> (Silver)</b></summary>

| Column Name | Data Type | Description | Null % |
| :--- | :--- | :--- | :--- |
| `transaction_id` | `string` | Unique identifier for the sale. | 0% |
| `customer_id` | `string` | Retail partner identifier. | 2% |

</details>

*(Generate `<details>` blocks for Gold and View tables here)*

---

## Power BI

| name | source |
| :--- | :--- |
| JP - Wholesale Sellout Dashboard | `jp_whs_sellout_report_vw` |

---

## ETLs

| source | schema | layer | name | DDL | code (scripts) | job | schedule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FTP/FileServer | `bronze_schema` | bronze | `whs_sellout_audit_log` | `audit_log.sql` | `notebooks/bronze/ingest.py` | `whs_ingestion_job` | continuous |
| Bronze | `silver_schema` | silver | `whs_sellout_s` | `whs_silver.sql` | `notebooks/silver/cleanse.py` | `whs_silver_job` | daily 5:15AM |
| Silver | `gold_schema` | gold | `jp_whs_sellout_g` | `whs_gold.sql` | `notebooks/gold/aggregate.py` | `whs_gold_job` | daily 6:30AM |
| Gold | `gold_schema` | view | `jp_whs_sellout_report_vw` | `whs_view.sql` | `notebooks/gold/create_vw.sql` | `whs_gold_job` | daily 6:30AM |

---

## FAQ

**[Question 1: What happens if a `.zip` file fails in the audit log?]**
[Answer: The pipeline will flag `bronze_status = Failed`. Data engineering must manually intervene.]

---

## Resources

* [Link to FTP connection details]
* [Link to Store Master documentation]
