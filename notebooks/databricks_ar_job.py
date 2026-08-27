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
import sys

# Add src to sys.path if running as uploaded repository
if os.path.exists("src") and "src" not in sys.path:
    sys.path.insert(0, "src")

import re
import requests
import pandas as pd
from datetime import datetime, timezone

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

print(f"🔧 Pipeline Parameters: Customer='{SELECTED_CUSTOMER}' | Days Back={DAYS_BACK} | Save To Delta={SAVE_TO_DELTA}")

# COMMAND ----------
# DBTITLE 1,Step 2: Initialize Core Graph Client & AR Controller
try:
    from core.graph_client import MSGraphEmailClient
    from ar_pipeline.ar_controller import ARPipelineController
    
    client = MSGraphEmailClient(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        mailbox=MAILBOX
    )
    controller = ARPipelineController(config_path="configs/customer_templates.yaml")
    USE_MODULAR_IMPORTS = True
    print("✅ Successfully loaded core and ar_pipeline modules!")
except Exception as e:
    USE_MODULAR_IMPORTS = False
    print(f"ℹ️ Modular import not detected ({e}). Running in standalone notebook mode...")

# COMMAND ----------
# DBTITLE 1,Step 3: Execute Ingestion & Parsing
if USE_MODULAR_IMPORTS:
    records = controller.run_pipeline(
        client=client,
        target_customer=SELECTED_CUSTOMER,
        top=50,
        spark_session=spark if SAVE_TO_DELTA else None,
        table_name="ar_silver_reconciliation"
    )
    df_clean = pd.DataFrame(records)
else:
    # Standalone fallback mode
    print("🔐 Authenticating with Microsoft Entra ID...")
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(token_url, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    })
    token = resp.json().get("access_token")
    
    mail_url = f"https://graph.microsoft.com/v1.0/users/{MAILBOX}/mailFolders/Inbox/messages"
    mail_resp = requests.get(mail_url, headers={"Authorization": f"Bearer {token}"}, params={"$top": 50})
    raw_emails = mail_resp.json().get("value", [])
    print(f"✅ Downloaded {len(raw_emails)} emails from inbox.")

# COMMAND ----------
# DBTITLE 1,Step 4: Display Output Matrix Table
if 'df_clean' in locals() and not df_clean.empty:
    print(f"\n📊 Extracted {len(df_clean)} Clean Reconciliation Records:")
    display(df_clean)
else:
    print("ℹ️ No new reconciliation records found for the selected filter.")
