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

    if 'שם בית עסק' in filtered_df.columns:
        filtered_df['שם בית עסק'] = filtered_df['שם בית עסק'].fillna('').astype(str)

    # Columns to show in RTL order (Right to Left visual, but Streamlit is LTR code)
    # Streamlit displays columns in order of list.
    # User checked: Date, Business, Sum, Category, Notes
    cols_to_show = ['תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות']
    
    # Editable Dataframe
    edited_df = st.data_editor(
        filtered_df, # Use filtered DF directly
        column_order=cols_to_show,
        column_config={
            "חודש": None, # Hide
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
                width="small"
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
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="expenses_editor"
    )
    
    # Save Logic (Same as before but simplified if possible)
    # Since we edit filtered_df, we need to merge back changes to main df.
    # Using indices is the standard way.
    
    if st.button("שמור שינויים", type="primary"):
        try:
            # 1. Handle Dates
            if 'תאריך רכישה' in edited_df.columns:
                edited_df['תאריך רכישה'] = edited_df['תאריך רכישה'].apply(
                    lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
                )
                
            # 2. Update Month
            edited_df['חודש'] = edited_df['תאריך רכישה'].apply(
                lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%m/%Y') if x else ''
            )

            # 3. Update Main DF
            # Iterate through edited rows and update main df by index
            # This handles edits and adds/removes if index aligns
            # Simple approach: Update existing rows, append new ones.
            
            # Check for deleted rows from filtered view
            current_filtered_indices = edited_df.index
            original_filtered_indices = filtered_df.index
            
            deleted_indices = set(original_filtered_indices) - set(current_filtered_indices)
            if deleted_indices:
                df = df.drop(list(deleted_indices))
            
            # Update modified rows
            df.update(edited_df)
            
            # Handle new rows (added safely via editor)
            # New rows usually have new indices or none if added via UI? 
            # Streamlit data editor adds rows with new index.
            # If we just depend on df.update for existing indices, we miss new ones.
            # But filtered_df might not show all rows, so we can't just replace df.
            
            # Ideally:
            # 1. Drop deleted
            # 2. Update existing
            # 3. Append new
            
            # Identify purely new rows (index not in original df)
            new_rows = edited_df[~edited_df.index.isin(df.index)]
            if not new_rows.empty:
                df = pd.concat([df, new_rows], ignore_index=True)

            save_expenses(df)
            st.success("השינויים נשמרו בהצלחה!")
            st.rerun()
            
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")
