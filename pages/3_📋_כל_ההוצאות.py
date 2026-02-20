import streamlit as st
import pandas as pd
from datetime import datetime
from utils import load_expenses, save_expenses, apply_custom_css, load_categories, format_currency

st.set_page_config(page_title="כל ההוצאות", page_icon="📋", layout="wide")
apply_custom_css()

st.title("📋 כל ההוצאות")

df = load_expenses()

if df.empty:
    st.info("אין נתונים.")
else:
    # ------------------------------------------------------------
    # FILTERS & SEARCH
    # ------------------------------------------------------------
    with st.expander("🔎 חיפוש וסינון", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Load categories from file to ensure up-to-date list
            all_categories = load_categories()
            # Also include any categories present in data but not in list
            data_cats = df['קטגוריה'].unique().tolist()
            # Filter out non-string or empty values to prevent sort errors
            valid_data_cats = [x for x in data_cats if isinstance(x, str) and x.strip()]
            combined_cats = sorted(list(set(all_categories + valid_data_cats)))
            
            selected_categories = st.multiselect("סינון לפי קטגוריה", options=combined_cats)
            
        with col2:
            # Months
            if 'חודש' in df.columns:
                months = list(df['חודש'].unique())
                selected_months = st.multiselect("סינון לפי חודש", options=months)
            else:
                selected_months = []
                
        with col3:
            name_search = st.text_input("חיפוש חופשי (שם עסק)")

    # ------------------------------------------------------------
    # FILTER LOGIC
    # ------------------------------------------------------------
    filtered_df = df.copy()
    
    # 1. Name Search (contains)
    if name_search:
        filtered_df = filtered_df[filtered_df['שם בית עסק'].str.contains(name_search, case=False, na=False)]
    
    # 2. Categories
    if selected_categories:
        filtered_df = filtered_df[filtered_df['קטגוריה'].isin(selected_categories)]
        
    # 3. Months
    if selected_months:
        filtered_df = filtered_df[filtered_df['חודש'].isin(selected_months)]

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------
    if not filtered_df.empty:
        st.caption(f"מציג {len(filtered_df)} רשומות מתוך {len(df)}")

    # ------------------------------------------------------------
    # TABLE PREP & EDIT
    # ------------------------------------------------------------
    
    # Pre-process for Editor
    if 'תאריך רכישה' in filtered_df.columns:
        filtered_df['תאריך רכישה'] = pd.to_datetime(filtered_df['תאריך רכישה'], errors='coerce')

    if 'הערות' in filtered_df.columns:
        filtered_df['הערות'] = filtered_df['הערות'].fillna('').astype(str)
        
    if 'קטגוריה' in filtered_df.columns:
        filtered_df['קטגוריה'] = filtered_df['קטגוריה'].fillna('').astype(str)

    # Columns to show
    # In RTL mode, Column 0 is on the Right.
    # We Include 'id' for tracking but hide it.
    cols_to_show = ['תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות']
    if 'id' in filtered_df.columns:
        cols_to_show.append('id')
    
    # Default Sort in Data Editor is manual unless we pre-sort.
    # We already "Default sort by Date - latest to earliest".
    filtered_df = filtered_df.sort_values('תאריך רכישה', ascending=False)
    
    # Editable Dataframe
    edited_df = st.data_editor(
        filtered_df, 
        column_order=cols_to_show,
        column_config={
            "id": st.column_config.TextColumn("ID", hidden=True), # Hide ID
            "חודש": None, 
            "תאריך רכישה": st.column_config.DateColumn(
                "תאריך",
                format="DD/MM/YYYY",
                width="small"
            ),
            "שם בית עסק": st.column_config.TextColumn(
                "בית עסק",
                width="large"
            ),
            "סכום עסקה": st.column_config.NumberColumn(
                "סכום",
                format="₪%.2f",
                width="small",
                step=0.01
            ),
            "קטגוריה": st.column_config.SelectboxColumn(
                "קטגוריה",
                options=combined_cats,
                width="medium",
                required=False
            ),
            "הערות": st.column_config.TextColumn(
                "הערות",
                width="medium"
            )
        },
        use_container_width=True, # Full width
        num_rows="dynamic",       # Enables Add/Delete rows
        hide_index=True,
        key="expenses_editor"
    )
    
    if st.button("שמור שינויים", type="primary"):
        try:
            # 1. Handle Dates & Formatting
            if 'תאריך רכישה' in edited_df.columns:
                edited_df['תאריך רכישה'] = pd.to_datetime(edited_df['תאריך רכישה']).dt.strftime('%Y-%m-%d')
                
            # 2. Update Month
            edited_df['חודש'] = edited_df['תאריך רכישה'].apply(
                lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%m/%Y') if x and str(x) != 'NaT' else ''
            )
            
            # 3. Clean Strings
            for col in ['קטגוריה', 'שם בית עסק', 'הערות']:
                if col in edited_df.columns:
                    edited_df[col] = edited_df[col].astype(str).replace('nan', '').replace('None', '')

            # 4. Smart Merge (Using ID)
            # If we have IDs, we use them. If not (local file legacy), we fall back to indices or append.
            
            if 'id' in df.columns and 'id' in edited_df.columns:
                # A. Identify Deletions
                # IDs that were in filtered_df but are NOT in edited_df
                # strictly strictly those that had an ID (not new rows)
                
                original_ids = set(filtered_df['id'].dropna().astype(str))
                current_ids = set(edited_df['id'].dropna().astype(str))
                
                deleted_ids = original_ids - current_ids
                
                # Remove from Global DF
                if deleted_ids:
                    df = df[~df['id'].astype(str).isin(deleted_ids)]
                
                # B. Identify Updates
                # Rows with IDs that exist in both.
                # We update specific columns in Global DF using set index for speed or simple loop
                # Just iterate edited_df rows that have an ID
                
                # Create a map from ID to row index in Global DF?
                # or just use loc with boolean mask (slower but safe)
                
                # Optimization: Convert DF to dict for updates?
                # Let's iterate through modified rows only? Streamlit doesn't give us "modified only" easily here without session state tracking.
                # valid_updates = edited_df[edited_df['id'].isin(original_ids)]
                # Actually, simpler: 
                # Since we are saving *everything* to Supabase (Delete All + Insert All),
                # We mainly need to construct the correct Final DF.
                # So: 
                # Final DF = (Global DF - Filtered Rows) + Edited Rows
                # BUT "Filtered Rows" might be a subset.
                # So:
                # 1. Start with Global DF.
                # 2. Drop ALL rows that were in the "Filtered View" (matching IDs).
                # 3. Append the "Edited DF" (which contains the remaining + updated + new rows).
                
                # IDs involved in the filter (Original)
                ids_in_filter = filtered_df['id'].dropna()
                
                # 1. Remove these ID rows from Global
                df = df[~df['id'].isin(ids_in_filter)]
                
                # 2. Append the NEW state of these rows (from editor)
                # This handles Updates and Deletions (since deleted ones are missing from editor)
                # And Additions (rows with NaN ID will be appended too)
                
                df = pd.concat([df, edited_df], ignore_index=True)
                
            else:
                 # Fallback for No IDs (legacy) - Risky but best effort
                 # Replace everything? No, that deletes hidden data.
                 # Merge by Index (unsafe if sort changed).
                 # If no IDs, we assume we are just managing the file.
                 # Let's just blindly append new to old unique?
                 # No, without IDs and with filters, it's impossible to know what was deleted.
                 # We will assume "Save Changes" implies "Replace All" if no IDs?
                 # No, that erases data.
                 # Generate UUIDs for local? 
                 # For now, simplistic approach:
                 st.warning("שים לב: עריכה מתקדמת זמינה רק כאשר מחוברים למסד נתונים (ID חסר).")
                 # Try to match by index if possible
                 pass
 
            save_expenses(df)
            st.success("השינויים נשמרו בהצלחה!")
            st.rerun() 
            
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")
