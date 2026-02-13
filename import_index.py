"""
Import 'Index' sheet from user Excel to create mapping.json
"""
import pandas as pd
import json
import os
from utils import save_mapping, load_mapping

# Configuration
EXCEL_PATH = r'G:\My Drive\התנהלות כלכלית\סיכום הוצאות חודשי משותף.xlsx'
SHEET_NAME = 'אינדקס'

def main():
    print("=" * 50)
    print("Importing Index for Auto-Categorization")
    print("=" * 50)
    
    if not os.path.exists(EXCEL_PATH):
        print(f"ERROR: File not found: {EXCEL_PATH}")
        return

    try:
        # Read the Excel file
        print(f"Reading file: {EXCEL_PATH}")
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        
        # User specified: Column D = Place Name, Column E = Default Category
        # In 0-indexed pandas: D=3, E=4
        
        # Verify columns exist
        if len(df.columns) < 5:
            print("ERROR: Not enough columns in 'אינדקס' sheet.")
            print(f"Columns found: {df.columns.tolist()}")
            return
            
        # Extract columns by index to be safe (assuming fixed structure)
        # Or by name if possible, but names might vary.
        # User said: "column D holdes the places' names, and column E holdes the default category"
        
        # Let's verify with a print
        print("First 5 rows (checking columns D and E):")
        print(df.iloc[:5, [3, 4]])
        
        mapping = load_mapping()
        count_new = 0
        count_update = 0
        
        for index, row in df.iterrows():
            business = str(row.iloc[3]).strip()
            category = str(row.iloc[4]).strip()
            
            # Skip invalid entries
            if not business or business == 'nan' or not category or category == 'nan':
                continue
                
            if business not in mapping:
                mapping[business] = category
                count_new += 1
            elif mapping[business] != category:
                # Update if different? User said "based on past categorization", implying this is the source of truth.
                mapping[business] = category
                count_update += 1
        
        save_mapping(mapping)
        print(f"\nSuccess! Mapping updated.")
        print(f"New rules: {count_new}")
        print(f"Updated rules: {count_update}")
        print(f"Total rules: {len(mapping)}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    main()
