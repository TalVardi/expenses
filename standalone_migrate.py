import pandas as pd
import toml
import json
import os
import requests

# Constants
EXPENSES_FILE = "expenses.csv"
CATEGORIES_FILE = "categories.json"
MAPPING_FILE = "mapping.json"
SECRETS_FILE = ".streamlit/secrets.toml"

def load_secrets():
    try:
        if os.path.exists(SECRETS_FILE):
             return toml.load(SECRETS_FILE)
    except Exception as e:
        print(f"Error loading secrets: {e}")
    return {}

def run_migration():
    print("Starting Standalone Migration to Supabase (via REST API)...")
    
    secrets = load_secrets()
    if "supabase" not in secrets:
        print("❌ Supabase secrets not found in .streamlit/secrets.toml")
        return

    base_url = secrets["supabase"]["SUPABASE_URL"]
    key = secrets["supabase"]["SUPABASE_KEY"]
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    # Helper function for batch insert
    def batch_insert(table_name, records):
        url = f"{base_url}/rest/v1/{table_name}"
        
        # 1. Delete existing (Truncate-like via delete all where id > 0)
        # Note: This requires the table to have an 'id' column and policy allowing delete.
        try:
             # Delete all rows where id is not null (basically all rows)
             requests.delete(f"{url}?id=neq.0", headers=headers)
        except Exception as e:
             print(f"Warning cleaning table {table_name}: {e}")

        # 2. Insert in chunks
        chunk_size = 1000
        total = len(records)
        print(f"  - Uploading {total} records to '{table_name}'...")
        
        for i in range(0, total, chunk_size):
            chunk = records[i:i + chunk_size]
            response = requests.post(url, headers=headers, json=chunk)
            if response.status_code not in (200, 201, 204):
                print(f"  ❌ Error batch {i}: {response.status_code} - {response.text}")
            else:
                pass # Success
        print(f"  ✅ {table_name}: Done.")

    # 1. Migrate Expenses
    print("Migrating Expenses...")
    try:
        if os.path.exists(EXPENSES_FILE):
            df = pd.read_csv(EXPENSES_FILE, encoding='utf-8-sig')
            records = []
            for _, row in df.iterrows():
                # Fix NaN values
                row = row.where(pd.notnull(row), None)
                
                date = str(row.get('תאריך רכישה', ''))
                business = str(row.get('שם בית עסק', ''))
                amount = float(row.get('סכום עסקה', 0)) if row.get('סכום עסקה') else 0.0
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
                batch_insert('expenses', records)
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
                data = [{'name': c} for c in cats]
                batch_insert('categories', data)
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
                data = [{'business': k, 'category': v} for k, v in mapping.items()]
                batch_insert('mapping', data)
        else:
            print("⚠️ mapping.json not found.")
    except Exception as e:
        print(f"❌ Error uploading mapping: {e}")

    print("Migration Complete! 🎉")

if __name__ == "__main__":
    run_migration()
