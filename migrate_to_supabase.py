import pandas as pd
import toml
import json
import os
from supabase import create_client

# Constants
EXPENSES_FILE = "expenses.csv"
CATEGORIES_FILE = "categories.json"
MAPPING_FILE = "mapping.json"
SECRETS_FILE = ".streamlit/secrets.toml"

def load_secrets():
    try:
        return toml.load(SECRETS_FILE)
    except Exception as e:
        print(f"Error loading secrets: {e}")
        return {}

def migrate():
    print("Starting Standalone Migration to Supabase...")
    
    secrets = load_secrets()
    if "supabase" not in secrets:
        print("❌ Supabase secrets not found in .streamlit/secrets.toml")
        return

    url = secrets["supabase"]["SUPABASE_URL"]
    key = secrets["supabase"]["SUPABASE_KEY"]
    
    try:
        client = create_client(url, key)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return

    # 1. Migrate Expenses
    print("Migrating Expenses...")
    try:
        if os.path.exists(EXPENSES_FILE):
            df = pd.read_csv(EXPENSES_FILE, encoding='utf-8-sig')
            # Normalize cols
            # We need to map Hebrew cols to English DB cols
            # DB: date, business, amount, category, notes, month
            # CSV: 'תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות', 'חודש'
            
            records = []
            for _, row in df.iterrows():
                # Handle potential missing cols gracefully
                date = str(row.get('תאריך רכישה', ''))
                business = str(row.get('שם בית עסק', ''))
                amount_val = row.get('סכום עסקה', 0)
                amount = float(amount_val) if amount_val else 0.0
                category = str(row.get('קטגוריה', ''))
                notes = str(row.get('הערות', ''))
                month = str(row.get('חודש', ''))
                
                records.append({
                    'date': date,
                    'business': business,
                    'amount': amount,
                    'category': category,
                    'notes': notes,
                    'month': month
                })
            
            if records:
                # Sync: Delete all & Insert
                client.table('expenses').delete().neq('id', 0).execute()
                
                # Chunking
                chunk_size = 1000
                for i in range(0, len(records), chunk_size):
                    chunk = records[i:i + chunk_size]
                    client.table('expenses').insert(chunk).execute()
                print(f"✅ Uploaded {len(records)} expenses.")
        else:
            print("⚠️ expenses.csv not found.")
    except Exception as e:
        print(f"❌ Error uploading expenses: {e}")

    # 2. Migrate Categories
    print("Migrating Categories...")
    try:
        if os.path.exists(CATEGORIES_FILE):
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                cats = json.load(f)
            
            if cats:
                client.table('categories').delete().neq('name', 'PLACEHOLDER').execute()
                data = [{'name': c} for c in cats]
                client.table('categories').insert(data).execute()
                print(f"✅ Uploaded {len(cats)} categories.")
        else:
             print("⚠️ categories.json not found.")
    except Exception as e:
        print(f"❌ Error uploading categories: {e}")

    # 3. Migrate Mapping
    print("Migrating Mapping...")
    try:
        if os.path.exists(MAPPING_FILE):
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            if mapping:
                client.table('mapping').delete().neq('business', 'PLACEHOLDER').execute()
                data = [{'business': k, 'category': v} for k, v in mapping.items()]
                
                chunk_size = 1000
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i + chunk_size]
                    client.table('mapping').insert(chunk).execute()
                print(f"✅ Uploaded {len(data)} mapping rules.")
        else:
            print("⚠️ mapping.json not found.")
    except Exception as e:
        print(f"❌ Error uploading mapping: {e}")

    print("Migration Complete! 🎉")

if __name__ == "__main__":
    migrate()
