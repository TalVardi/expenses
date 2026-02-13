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
    # User Request: "date should be seen most right, notes most left"
    # In RTL mode, Column 0 is on the Right.
    cols_to_show = ['תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות']
    
    # Default Sort in Data Editor is manual unless we pre-sort.
    # We already "Default sort by Date - latest to earliest".
    filtered_df = filtered_df.sort_values('תאריך רכישה', ascending=False)
    
    # Editable Dataframe
    edited_df = st.data_editor(
        filtered_df, 
        column_order=cols_to_show,
        column_config={
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
    
    # In 'num_rows="dynamic"', the user deletes rows in the UI, and they disappear from 'edited_df'.
    # We detect deletions by checking missing indices.
    
    if st.button("שמור שינויים", type="primary"):
        try:
            # 1. Handle Dates
            if 'תאריך רכישה' in edited_df.columns:
                edited_df['תאריך רכישה'] = pd.to_datetime(edited_df['תאריך רכישה']).dt.strftime('%Y-%m-%d')
                
            # 2. Update Month
            edited_df['חודש'] = edited_df['תאריך רכישה'].apply(
                lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%m/%Y') if x else ''
            )
            
            # 3. Update Categories/Biz Strings (Fix mixed types)
            for col in ['קטגוריה', 'שם בית עסק', 'הערות']:
                if col in edited_df.columns:
                    edited_df[col] = edited_df[col].astype(str)

            # 4. Integrate Changes
            # Get current indices from editor
            current_indices = edited_df.index
            
            # Original DF (GLOBAL DF) needs to be updated.
            # We must be careful: data editor returns a new dataframe with potentially new indices for added rows.
            # But we are editing `filtered_df`. 
            # If we delete a row in filtered view, we want to delete it from global `df`.
            
            # Map filtered indices to global indices?
            # filtered_df.index contains global indices.
            
            # A. Deletions
            # Indices present in original filtered_df but missing in edited_df
            deleted_indices = set(filtered_df.index) - set(current_indices)
            if deleted_indices:
                df = df.drop(list(deleted_indices))
                
            # B. Updates
            # Common indices
            common_indices = list(set(filtered_df.index).intersection(set(current_indices)))
            if common_indices:
                # Update specific columns
                for col in cols_to_show:
                    df.loc[common_indices, col] = edited_df.loc[common_indices, col]
                # Also update derived 'חודש'
                df.loc[common_indices, 'חודש'] = edited_df.loc[common_indices, 'חודש']
                
            # C. Additions
            # Indices in edited_df that are NOT in filtered_df.index
            # Streamlit usually resets index or uses RangeIndex for new rows.
            # If strictly new rows:
            new_rows = edited_df[~edited_df.index.isin(filtered_df.index)]
            if not new_rows.empty:
                df = pd.concat([df, new_rows], ignore_index=True)
 
            save_expenses(df)
            st.success("השינויים נשמרו בהצלחה!")
            st.rerun() 
            
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")
