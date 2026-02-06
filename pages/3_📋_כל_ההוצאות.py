import streamlit as st
import pandas as pd
from datetime import datetime
from utils import load_expenses, save_expenses, apply_custom_css, CATEGORIES, format_currency

st.set_page_config(page_title="כל ההוצאות", page_icon="📋", layout="wide")
apply_custom_css()

st.title("כל ההוצאות")

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
            categories = list(df['קטגוריה'].unique())
            selected_categories = st.multiselect("סינון לפי קטגוריה", options=categories)
            
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
        total_filtered = filtered_df['סכום עסקה'].sum()
        st.caption(f"מציג {len(filtered_df)} רשומות מתוך {len(df)}")
        # st.metric("סה\"כ לתצוגה", format_currency(total_filtered)) # Optional: Show big number

    # ------------------------------------------------------------
    # TABLE PREP & EDIT
    # ------------------------------------------------------------
    
    # Pre-process for Editor (Date & Text Handling)
    if 'תאריך רכישה' in filtered_df.columns:
        filtered_df['תאריך רכישה'] = pd.to_datetime(filtered_df['תאריך רכישה'], errors='coerce')

    if 'הערות' in filtered_df.columns:
        filtered_df['הערות'] = filtered_df['הערות'].fillna('').astype(str)
        
    if 'קטגוריה' in filtered_df.columns:
        filtered_df['קטגוריה'] = filtered_df['קטגוריה'].fillna('').astype(str)

    # Sorting
    sort_map = {
        'תאריך': 'תאריך רכישה',
        'סכום': 'סכום עסקה',
        'שם עסק': 'שם בית עסק',
        'קטגוריה': 'קטגוריה'
    }
    
    col_sort, col_dummy = st.columns([1, 4])
    with col_sort:
        selected_sort = st.selectbox("מיון לפי", list(sort_map.keys()), index=0)
    
    sort_col = sort_map[selected_sort]
    # Keep original index for saving logic
    df_sorted = filtered_df.sort_values(sort_col, ascending=False)
    
    # Columns to show
    cols_to_show = ['תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות']
    
    # Editable Dataframe
    edited_df = st.data_editor(
        df_sorted,
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
                options=CATEGORIES,
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
    
    if st.button("שמור שינויים", type="primary"):
        try:
            # 1. Handle Dates in Edited DF
            if 'תאריך רכישה' in edited_df.columns:
                edited_df['תאריך רכישה'] = edited_df['תאריך רכישה'].apply(
                    lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
                )
                
            # 2. Update Month column
            edited_df['חודש'] = edited_df['תאריך רכישה'].apply(
                lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%m/%Y') if x else ''
            )

            # 3. Identify Changes
            # Original filter indices
            original_indices = df_sorted.index
            # Current indices (after edits/deletes)
            current_indices = edited_df.index
            
            # Identify Deleted Rows (indices in original but not in current)
            deleted_indices = set(original_indices) - set(current_indices)
            
            # Identify Modified Rows (intersection)
            common_indices = set(original_indices).intersection(set(current_indices))
            
            # Identify New Rows (in current but not in original? Streamlit might use new indices)
            # Usually strict new rows might not have integer index if dataframe had RangeIndex.
            # But let's assume update works on common indices.
            
            # A. Drop deleted
            if deleted_indices:
                df = df.drop(list(deleted_indices))
                
            # B. Update modified
            if common_indices:
                # We update specific columns in the main DF using the edited subset
                # df.update(edited_df) might overwrite NaNs? Safe enough here.
                df.update(edited_df)
                
            # C. Handle Additions (if any, though tough with index mismatch)
            # Find rows in edited_df that are NOT in original_indices
            new_rows_indices = set(current_indices) - set(original_indices)
            if new_rows_indices:
                new_rows = edited_df.loc[list(new_rows_indices)]
                df = pd.concat([df, new_rows], ignore_index=True)

            save_expenses(df)
            st.success("השינויים נשמרו בהצלחה!")
            st.rerun() # Refresh to show updated data
            
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")
