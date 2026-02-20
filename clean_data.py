import pandas as pd
import requests
import toml
import os

def load_secrets():
    secrets_path = ".streamlit/secrets.toml"
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    except Exception as e:
        print(f"Error loading secrets: {e}")
        return None

def clean_none_categories():
    print("Loading secrets...")
    secrets = load_secrets()
    if not secrets:
        return

    try:
        if "connections" in secrets and "supabase" in secrets["connections"]:
             conf = secrets["connections"]["supabase"]
        elif "supabase" in secrets:
             conf = secrets["supabase"]
        else:
             print("Could not find supabase config in secrets.toml")
             return

    except Exception as e:
         print(f"Error reading secrets: {e}")
         return

    SUPABASE_URL = conf["SUPABASE_URL"]
    SUPABASE_KEY = conf["SUPABASE_KEY"]
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    print("Fetching all expenses...")
    url = f"{SUPABASE_URL}/rest/v1/expenses?select=*"
    all_data = []
    offset = 0
    limit = 1000
    
    # Pagination Logic
    while True:
        paged_url = f"{url}&limit={limit}&offset={offset}"
        try:
            response = requests.get(paged_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if not data:
                    break
                all_data.extend(data)
                if len(data) < limit:
                    break
                offset += limit
            else:
                print(f"Error fetching data: {response.text}")
                break
        except Exception as e:
            print(f"Request failed: {e}")
            break

    if not all_data:
        print("No data found.")
        return

    df = pd.DataFrame(all_data)
    print(f"Total records: {len(df)}")
    
    # Filter for 'None' or 'nan' in 'category' (English key from DB)
    # DB columns are: date, business, amount, category, notes, month, id...
    
    bad_mask = (df['category'].astype(str).str.lower() == 'none') | (df['category'].astype(str).str.lower() == 'nan')
    bad_rows = df[bad_mask]
    
    if bad_rows.empty:
        print("No 'None' categories found in DB.")
        return

    print(f"Found {len(bad_rows)} rows with 'None' category.")
    
    # Fix in Memory
    # We will simply clean the 'category' field in these rows.
    # To avoid mass delete/insert which is risky with limits/timeouts in a script,
    # let's Update only the bad rows by ID.
    
    if 'id' not in df.columns:
        print("Error: 'id' column missing, cannot update specific rows.")
        return

    print("Updating bad rows one by one (safer for script)...")
    
    update_url = f"{SUPABASE_URL}/rest/v1/expenses"
    count = 0
    
    for index, row in bad_rows.iterrows():
        row_id = row['id']
        # Patch request
        patch_url = f"{update_url}?id=eq.{row_id}"
        payload = {"category": ""} # Set to empty string
        
        try:
            r = requests.patch(patch_url, headers=headers, json=payload)
            if r.status_code in [200, 204]:
                count += 1
                if count % 10 == 0:
                    print(f"Fixed {count}...")
            else:
                print(f"Failed to update {row_id}: {r.text}")
        except Exception as e:
            print(f"Error updating {row_id}: {e}")

    print(f"Finished. Fixed {count} rows.")

if __name__ == "__main__":
    clean_none_categories()
