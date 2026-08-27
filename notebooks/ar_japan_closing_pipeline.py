# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 📊 Accounts Receivable (AR) Email Ingestion Pipeline
# MAGIC **Universal Deterministic Rule Engine for Microsoft 365 & Databricks Delta Lake**
# MAGIC 
# MAGIC - **Source:** Microsoft 365 (Outlook Graph API)
# MAGIC - **Engine:** 100% Deterministic Table & Key-Value Rules (Zero LLM cost)
# MAGIC - **Target:** Databricks Delta Lake (`ar_silver_reconciliation`)

# COMMAND ----------
# DBTITLE 1,Step 1: Configuration & Credentials
import os
import re
import io
import json
import logging
from datetime import datetime, timezone, date
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- Credentials ---
# In production, use dbutils.secrets.get(scope="m365", key="client_secret")
TENANT_ID = os.getenv("TENANT_ID", "51c06ca7-89ca-4780-bdf1-3606f7cb85eb")
CLIENT_ID = os.getenv("CLIENT_ID", "480bfc10-d5c1-44f0-8f76-4bfeba066cec")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "YOUR_CLIENT_SECRET") # Replace or use Databricks Secret
MAILBOX = os.getenv("MAILBOX", "BiswajitBrahmma@kaizencodes.onmicrosoft.com")

# --- UI Widgets (Dropdown & Parameters) ---
try:
    dbutils.widgets.dropdown("Customer", "ALL", ["ALL", "KamoShoji", "Imoto", "Himaraya", "Amazon", "Chiyoda", "GFoot", "Mega", "ABCMart"])
    dbutils.widgets.text("Days_Back", "30")
    dbutils.widgets.dropdown("Save_To_Delta", "True", ["True", "False"])
    
    SELECTED_CUSTOMER = dbutils.widgets.get("Customer")
    DAYS_BACK = int(dbutils.widgets.get("Days_Back"))
    SAVE_TO_DELTA = dbutils.widgets.get("Save_To_Delta") == "True"
except Exception:
    SELECTED_CUSTOMER = "ALL"
    DAYS_BACK = 30
    SAVE_TO_DELTA = False

print(f"🔧 Target Filter: Customer='{SELECTED_CUSTOMER}' | Days Back={DAYS_BACK} | Save To Delta={SAVE_TO_DELTA}")

# COMMAND ----------
# DBTITLE 1,Step 2: Customer Parsing Rules (Declarative Configuration)
CUSTOMER_RULES = {
    "KamoShoji": {
        "match_regex": r".*加茂商事.*",
        "strategy": "vertical_key_value",
        "code_source": {"table_index": 0, "target_regex": "請求先コード"},
        "amount_source": {"table_index": 0, "target_regex": r".*(支払額|入金額|振込).*"}
    },
    "Chiyoda": {
        "match_regex": r".*チヨダ.*",
        "strategy": "vertical_key_value",
        "code_source": {"table_index": 0, "target_regex": "請求先コード"},
        "amount_source": {"table_index": 0, "target_regex": r".*(支払額|振込額).*"}
    },
    "GFoot": {
        "match_regex": r".*(G-FOOT|ジーフット|Aeon Sports.*G-foot).*",
        "strategy": "vertical_key_value",
        "code_source": {"table_index": 0, "target_regex": "請求先コード"},
        "amount_source": {"table_index": 1, "target_regex": r".*(入金額|支払額|振込).*"}
    },
    "ABCMart": {
        "match_regex": r".*(ABC-MART|ABC MART|ABC).*",
        "strategy": "vertical_key_value",
        "code_source": {"table_index": 0, "target_regex": "請求先コード"},
        "amount_source": {"table_index": 1, "target_regex": r".*(支払額|入金額|振込).*"}
    },
    "Mega": {
        "match_regex": r".*(AEON Sports.*Mega|メガ).*",
        "strategy": "zip_columns_across_tables",
        "code_source": {"table_index": 0, "target_regex": "請求先コード"},
        "amount_source": {"table_index": 1, "target_regex": r".*(振込金額|支払額|入金額).*"}
    },
    "Himaraya": {
        "match_regex": r".*ヒマラヤ.*",
        "strategy": "zip_headers_to_row",
        "amount_source": {"table_index": 1, "target_regex": r".*(支払額|入金額).*"}
    },
    "Amazon": {
        "match_regex": r".*(Amazon|アマゾン).*",
        "strategy": "zip_headers_to_row",
        "amount_source": {"table_index": 0, "target_regex": r".*(支払額|入金額).*"}
    },
    "Imoto": {
        "match_regex": r".*イモト.*",
        "strategy": "zip_rows_in_same_table",
        "code_source": {"table_index": 1, "target_regex": r"^コード$"},
        "amount_source": {"table_index": 1, "target_regex": r".*(支払額|入金額).*"},
        "prefix_code": "79"
    }
}

# COMMAND ----------
# DBTITLE 1,Step 3: Core Cleaning & Extraction Engine
class JapaneseCurrencyCleaner:
    @staticmethod
    def clean(value):
        if value is None or str(value).strip() in ["", "-", "―", "ー", "#DIV/0!", "#N/A", "nan"]:
            return None
        text = str(value).strip()
        is_negative = ("△" in text) or ("▲" in text) or (text.startswith("(") and text.endswith(")")) or ("-" in text)
        digits = re.sub(r"[¥￥\\,△▲\(\)\s円-]", "", text)
        if not digits:
            return None
        try:
            num = float(digits)
            return -num if is_negative else num
        except ValueError:
            return None

class UniversalTableParser:
    @staticmethod
    def extract_tables(html):
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        parsed_tables = []
        for tbl in soup.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells and any(c != "" for c in cells):
                    rows.append(cells)
            if rows:
                max_cols = max(len(r) for r in rows)
                norm_rows = [r + [""] * (max_cols - len(r)) for r in rows]
                parsed_tables.append(pd.DataFrame(norm_rows))
        
        # Fallback to pipe-delimited text
        if not parsed_tables and "|" in html:
            text = soup.get_text(separator="\n").strip()
            lines = [l.strip() for l in text.split("\n") if "|" in l and not all(c in "-| \t\xa0" for c in l)]
            if len(lines) >= 2:
                raw_rows = [[c.strip() for c in l.split("|") if c.strip()] for l in lines]
                max_cols = max(len(r) for r in raw_rows)
                norm_rows = [r + [""] * (max_cols - len(r)) for r in raw_rows]
                parsed_tables.append(pd.DataFrame(norm_rows))
        return parsed_tables

    @staticmethod
    def parse_email(email_dict, cust_name, conf):
        html = email_dict.get("html_body", "")
        tables = UniversalTableParser.extract_tables(html)
        if not tables:
            return []
        
        strategy = conf.get("strategy")
        records = []
        prefix = conf.get("prefix_code", "")

        if strategy == "vertical_key_value":
            code_idx = conf.get("code_source", {}).get("table_index", 0)
            amt_idx = conf.get("amount_source", {}).get("table_index", 0)
            code_regex = conf.get("code_source", {}).get("target_regex", "請求先コード")
            amt_regex = conf.get("amount_source", {}).get("target_regex", ".*支払額.*")
            
            code_val = None
            amt_val = None
            date_label = None

            if code_idx < len(tables):
                for _, row in tables[code_idx].iterrows():
                    vals = [str(x).strip() for x in row if str(x).strip()]
                    for i, c in enumerate(vals):
                        if re.search(code_regex, c) and i + 1 < len(vals):
                            code_val = vals[i + 1]
                            break

            if amt_idx < len(tables):
                for _, row in tables[amt_idx].iterrows():
                    vals = [str(x).strip() for x in row if str(x).strip()]
                    for i, c in enumerate(vals):
                        if re.search(amt_regex, c):
                            date_label = c
                            if i + 1 < len(vals):
                                amt_val = JapaneseCurrencyCleaner.clean(vals[i + 1])
                            break

            if code_val and amt_val is not None:
                final_code = f"{prefix}{code_val}" if prefix and not str(code_val).startswith(prefix) else code_val
                records.append({
                    "customer_name": cust_name,
                    "customer_code": final_code,
                    "payment_due_label": date_label,
                    "payment_amount": amt_val,
                    "currency": "JPY"
                })

        elif strategy == "zip_headers_to_row":
            tbl_idx = conf.get("amount_source", {}).get("table_index", 0)
            amt_regex = conf.get("amount_source", {}).get("target_regex", ".*支払額.*")
            if tbl_idx < len(tables):
                df = tables[tbl_idx]
                headers = [str(x).strip() for x in df.iloc[0] if str(x).strip()]
                for _, row in df.iterrows():
                    vals = [str(x).strip() for x in row if str(x).strip()]
                    if any(re.search(amt_regex, v) for v in vals):
                        match_idx = next(i for i, v in enumerate(vals) if re.search(amt_regex, v))
                        date_label = vals[match_idx]
                        amts = [JapaneseCurrencyCleaner.clean(v) for v in vals[match_idx + 1:]]
                        code_headers = headers[1:] if len(headers) > len(amts) else headers
                        for code, amt in zip(code_headers, amts):
                            if code and amt is not None and code not in ["合計", "-"]:
                                final_code = f"{prefix}{code}" if prefix and not str(code).startswith(prefix) else code
                                records.append({
                                    "customer_name": cust_name,
                                    "customer_code": final_code,
                                    "payment_due_label": date_label,
                                    "payment_amount": amt,
                                    "currency": "JPY"
                                })
                        break

        elif strategy == "zip_rows_in_same_table":
            tbl_idx = conf.get("amount_source", {}).get("table_index", 0)
            code_regex = conf.get("code_source", {}).get("target_regex", "コード")
            amt_regex = conf.get("amount_source", {}).get("target_regex", ".*支払額.*")
            if tbl_idx < len(tables):
                df = tables[tbl_idx]
                codes = []
                amts = []
                date_label = None
                for _, row in df.iterrows():
                    vals = [str(x).strip() for x in row if str(x).strip()]
                    if any(re.search(code_regex, v) for v in vals):
                        match_idx = next(i for i, v in enumerate(vals) if re.search(code_regex, v))
                        codes = vals[match_idx + 1:]
                    elif any(re.search(amt_regex, v) for v in vals):
                        match_idx = next(i for i, v in enumerate(vals) if re.search(amt_regex, v))
                        date_label = vals[match_idx]
                        amts = [JapaneseCurrencyCleaner.clean(v) for v in vals[match_idx + 1:]]
                for code, amt in zip(codes, amts):
                    if code and amt is not None and code not in ["合計", "-"]:
                        final_code = f"{prefix}{code}" if prefix and not str(code).startswith(prefix) else code
                        records.append({
                            "customer_name": cust_name,
                            "customer_code": final_code,
                            "payment_due_label": date_label,
                            "payment_amount": amt,
                            "currency": "JPY"
                        })

        return records

# COMMAND ----------
# DBTITLE 1,Step 4: Fetch Emails via Microsoft Graph API
print("🔐 Authenticating with Microsoft Entra ID...")
token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
token_payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "https://graph.microsoft.com/.default"
}
token_resp = requests.post(token_url, data=token_payload)
if token_resp.status_code != 200:
    raise RuntimeError(f"Authentication Failed: {token_resp.text}")

token = token_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print(f"📥 Fetching inbox emails for {MAILBOX}...")
mail_url = f"https://graph.microsoft.com/v1.0/users/{MAILBOX}/mailFolders/Inbox/messages"
params = {"$top": 50, "$orderby": "receivedDateTime desc"}
resp = requests.get(mail_url, headers=headers, params=params)

if resp.status_code != 200:
    raise RuntimeError(f"Failed to fetch emails: {resp.text}")

raw_emails = resp.json().get("value", [])
print(f"✅ Downloaded {len(raw_emails)} recent emails from inbox.")

# COMMAND ----------
# DBTITLE 1,Step 5: Execute Rule Engine & Extract AR Records
extracted_data = []

for email in raw_emails:
    subj = email.get("subject", "")
    body = email.get("body", {}).get("content", "")
    received = email.get("receivedDateTime", "")
    sender = email.get("from", {}).get("emailAddress", {}).get("address", "")

    email_obj = {
        "subject": subj,
        "html_body": body,
        "received_at": received,
        "sender": sender
    }

    # Match customer
    for cust_name, conf in CUSTOMER_RULES.items():
        if SELECTED_CUSTOMER != "ALL" and SELECTED_CUSTOMER != cust_name:
            continue
        if re.search(conf["match_regex"], subj, re.IGNORECASE):
            records = UniversalTableParser.parse_email(email_obj, cust_name, conf)
            for r in records:
                r["email_subject"] = subj
                r["email_received_at"] = received
                r["email_sender"] = sender
                r["ingested_at"] = datetime.now(timezone.utc).isoformat()
                extracted_data.append(r)
            if records:
                print(f"✅ [{cust_name}] Extracted {len(records)} record(s) from: '{subj}'")

# COMMAND ----------
# DBTITLE 1,Step 6: Display Results & Write to Delta Lake
if extracted_data:
    df_clean = pd.DataFrame(extracted_data)
    print(f"\n📊 Successfully parsed {len(df_clean)} total reconciliation record(s):")
    display(df_clean)

    if SAVE_TO_DELTA:
        spark_df = spark.createDataFrame(df_clean)
        # Create Delta Table if not exists
        spark.sql("""
            CREATE TABLE IF NOT EXISTS ar_silver_reconciliation (
                customer_name STRING,
                customer_code STRING,
                payment_due_label STRING,
                payment_amount DOUBLE,
                currency STRING,
                email_subject STRING,
                email_received_at STRING,
                email_sender STRING,
                ingested_at STRING
            ) USING DELTA
        """)
        
        # Idempotent write / Append
        spark_df.write.format("delta").mode("append").saveAsTable("ar_silver_reconciliation")
        print("💾 Successfully saved records to Delta Lake: `ar_silver_reconciliation`!")
else:
    print("ℹ️ No matching customer emails found in the current batch.")
