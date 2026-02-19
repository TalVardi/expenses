import streamlit as st
import pandas as pd
from utils import db, load_expenses, load_categories, load_mapping
import time

def migrate():
    print("Starting migration to Google Sheets...")
    
    if not db.connected:
        print("❌ Not connected to Google Sheets. Please configure .streamlit/secrets.toml")
        return

    # 1. Migrate Expenses
    print("Migrating Expenses...")
    # Load from local file directly to avoid db.load_expenses() returning sheet data (which is empty)
    # Actually db.load_expenses() returns sheet data if connected.
    # We need to read the LOCAL file explicitly.
    try:
        local_df = db._load_local_expenses()
        if not local_df.empty:
            db.save_expenses(local_df)
            print(f"✅ Uploaded {len(local_df)} expenses.")
        else:
            print("⚠️ Local expenses file is empty or missing.")
    except Exception as e:
        print(f"❌ Error uploading expenses: {e}")

    # 2. Migrate Categories
    print("Migrating Categories...")
    try:
        local_cats = db._load_local_categories()
        if local_cats:
            db.save_categories(local_cats)
            print(f"✅ Uploaded {len(local_cats)} categories.")
    except Exception as e:
        print(f"❌ Error uploading categories: {e}")

    # 3. Migrate Mapping
    print("Migrating Mapping...")
    try:
        local_map = db._load_local_mapping()
        if local_map:
            db.save_mapping(local_map)
            print(f"✅ Uploaded {len(local_map)} mapping rules.")
    except Exception as e:
        print(f"❌ Error uploading mapping: {e}")

    print("Migration Complete! 🎉")

if __name__ == "__main__":
    migrate()
