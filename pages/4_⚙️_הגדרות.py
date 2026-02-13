import streamlit as st
import pandas as pd
from utils import (
    load_expenses, save_expenses, normalize_uploaded_file, apply_custom_css, 
    load_categories, save_categories, load_mapping, save_mapping, auto_categorize_expenses
)
import os

st.set_page_config(page_title="הגדרות", page_icon="⚙️", layout="wide")
apply_custom_css()

st.title("⚙️ הגדרות מערכת")

# TABS
tab1, tab2, tab3 = st.tabs(["📤 ניהול נתונים", "🏷️ קטגוריות", "🤖 סיווג אוטומטי"])

# --------------------------------------------------------------------------------
# TAB 1: DATA MANAGEMENT
# --------------------------------------------------------------------------------
with tab1:
    st.subheader("העלאת נתונים חדשים")
    st.caption("העלה קבצי אקסל או CSV מהבנק/אשראי. המערכת תסווג אוטומטית לפי ההיסטוריה שלך.")
    
    uploaded_file = st.file_uploader("בחר קובץ (CSV/Excel)", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file:
        if st.button("עבד ושמור נתונים", type="primary"):
            with st.spinner("מעבד נתונים..."):
                existing_df = load_expenses()
                new_df = normalize_uploaded_file(uploaded_file)
                
                if not new_df.empty:
                    # 1. Auto Categorize using Mapping
                    mapping = load_mapping()
                    new_df = auto_categorize_expenses(new_df, mapping)
                    
                    # 2. Deduplication Logic
                    if not existing_df.empty:
                        def create_key(row):
                            # Create a unique key for deduplication
                            d = str(row.get('תאריך רכישה', ''))
                            n = str(row.get('שם בית עסק', '')).strip()
                            s = str(row.get('סכום עסקה', ''))
                            return f"{d}|{n}|{s}"
                        
                        existing_keys = set(existing_df.apply(create_key, axis=1))
                        
                        # Filter out existing
                        new_rows = []
                        duplicates = 0
                        for _, row in new_df.iterrows():
                            key = create_key(row)
                            if key not in existing_keys:
                                new_rows.append(row)
                                existing_keys.add(key)
                            else:
                                duplicates += 1
                        
                        if new_rows:
                            final_new_df = pd.DataFrame(new_rows)
                            combined_df = pd.concat([existing_df, final_new_df], ignore_index=True)
                            save_expenses(combined_df)
                            st.success(f"✅ נוספו {len(new_rows)} רשומות חדשות! ({duplicates} כפילויות סוננו)")
                            st.info("💡 המערכת סיווגה אוטומטית הוצאות מוכרות. עבור לדף 'מיפוי' כדי לסווג את השאר.")
                        else:
                            st.warning(f"⚠️ כל הרשומות בקובץ קיימות כבר במערכת ({duplicates} כפילויות).")
                    else:
                        save_expenses(new_df)
                        st.success(f"✅ נוספו {len(new_df)} רשומות חדשות!")
                        st.info("💡 המערכת סיווגה אוטומטית הוצאות מוכרות.")
                        
                else:
                    st.error("❌ לא ניתן היה לפענח את הקובץ. וודא שהפורמט תקין.")

    st.divider()
    
    st.subheader("אזור מסוכן")
    if st.button("🗑️ מחק את כל הנתונים", type="secondary"):
        st.session_state['confirm_delete'] = True

    if st.session_state.get('confirm_delete'):
        st.error("האם אתה בטוח? פעולה זו תמחק את כל ההוצאות לצמיתות!")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("כן, מחק הכל"):
                if os.path.exists("expenses.csv"):
                    os.remove("expenses.csv")
                    # Re-create empty
                    df_empty = pd.DataFrame(columns=['חודש', 'תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות'])
                    save_expenses(df_empty)
                st.success("כל הנתונים נמחקו.")
                st.session_state['confirm_delete'] = False
                st.rerun()
        with col_cancel:
            if st.button("ביטול"):
                st.session_state['confirm_delete'] = False
                st.rerun()

# --------------------------------------------------------------------------------
# TAB 2: CATEGORIES
# --------------------------------------------------------------------------------
with tab2:
    st.subheader("ניהול קטגוריות")
    st.caption("ניתן לערוך, להוסיף או למחוק קטגוריות בטבלה:")
    
    current_cats = load_categories()
    cat_df = pd.DataFrame(current_cats, columns=["שם קטגוריה"])
    
    edited_cats_df = st.data_editor(
        cat_df,
        num_rows="dynamic",
        use_container_width=True,
        key="cat_editor",
        hide_index=True
    )
    
    if st.button("שמור שינויים בקטגוריות", type="primary"):
        new_cats_list = edited_cats_df["שם קטגוריה"].dropna().astype(str).tolist()
        new_cats_list = sorted(list(set([c.strip() for c in new_cats_list if c.strip()])))
        
        save_categories(new_cats_list)
        st.success("הקטגוריות עודכנו בהצלחה!")
        st.rerun()

# --------------------------------------------------------------------------------
# TAB 3: AUTO-MAPPING
# --------------------------------------------------------------------------------
with tab3:
    st.subheader("ניהול סיווג אוטומטי")
    st.caption("הגדר לאיזו קטגוריה ישוייך כל בית עסק אוטומטית בעתיד.")
    
    mapping = load_mapping()
    # Convert to DataFrame for editing
    if mapping:
        map_df = pd.DataFrame(list(mapping.items()), columns=['שם בית עסק', 'קטגוריה ברירת מחדל'])
    else:
        map_df = pd.DataFrame(columns=['שם בית עסק', 'קטגוריה ברירת מחדל'])
        
    # Get categories for dropdown
    all_categories = load_categories()
    
    edited_map_df = st.data_editor(
        map_df,
        num_rows="dynamic",
        use_container_width=True,
        key="map_editor",
        hide_index=True,
        column_config={
            "שם בית עסק": st.column_config.TextColumn(
                "שם בית עסק",
                width="large",
                required=True
            ),
            "קטגוריה ברירת מחדל": st.column_config.SelectboxColumn(
                "קטגוריה",
                options=all_categories,
                width="medium",
                required=True
            )
        }
    )
    
    if st.button("שמור כללי סיווג", type="primary"):
        new_mapping = {}
        for index, row in edited_map_df.iterrows():
            biz = str(row['שם בית עסק']).strip()
            cat = str(row['קטגוריה ברירת מחדל']).strip()
            if biz and cat:
                new_mapping[biz] = cat
        
        save_mapping(new_mapping)
        st.success(f"נשמרו {len(new_mapping)} כללי סיווג!")
