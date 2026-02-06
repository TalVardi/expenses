import streamlit as st
import pandas as pd
from utils import load_expenses, save_expenses, normalize_uploaded_file, auto_categorize, apply_custom_css

st.set_page_config(page_title="הגדרות", page_icon="⚙️", layout="wide")
apply_custom_css()

st.title("הגדרות")

# TABS
tab1, tab2 = st.tabs(["📤 העלאת נתונים", "🏷️ ניהול קטגוריות"])

with tab1:
    st.markdown("### העלאת קבצי בנק/אשראי")
    uploaded_file = st.file_uploader("בחר קובץ (CSV/Excel)", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file:
        if st.button("עבד ושמור נתונים", type="primary"):
            with st.spinner("מעבד נתונים..."):
                existing_df = load_expenses()
                new_df = normalize_uploaded_file(uploaded_file)
                
                if not new_df.empty:
                    # Auto Categorize
                    new_df = auto_categorize(new_df, existing_df)
                    
                    # Deduplication Logic
                    # We create a temporary key based on Date+Name+Amount
                    if not existing_df.empty:
                        def create_key(row):
                            return f"{row.get('תאריך רכישה')}|{row.get('שם בית עסק')}|{row.get('סכום עסקה')}"
                        
                        existing_keys = set(existing_df.apply(create_key, axis=1))
                        
                        # Filter out existing
                        new_rows = []
                        duplicates = 0
                        for _, row in new_df.iterrows():
                            key = create_key(row)
                            if key not in existing_keys:
                                new_rows.append(row)
                                existing_keys.add(key) # Prevent internal dupes in same file
                            else:
                                duplicates += 1
                        
                        if new_rows:
                            final_new_df = pd.DataFrame(new_rows)
                            combined_df = pd.concat([existing_df, final_new_df], ignore_index=True)
                            save_expenses(combined_df)
                            st.success(f"נוספו {len(new_rows)} רשומות חדשות! ({duplicates} כפילויות סוננו)")
                        else:
                            st.warning(f"כל הרשומות בקובץ קיימות כבר במערכת ({duplicates} כפילויות).")
                    else:
                        save_expenses(new_df)
                        st.success(f"נוספו {len(new_df)} רשומות חדשות!")
                        
                else:
                    st.error("לא ניתן היה לפענח את הקובץ. וודא שהפורמט תקין.")


with tab2:
    st.markdown("### ניהול קטגוריות")
    
    from utils import load_categories, save_categories
    
    current_cats = load_categories()
    cat_df = pd.DataFrame(current_cats, columns=["שם קטגוריה"])
    
    st.caption("ניתן לערוך, להוסיף או למחוק קטגוריות בטבלה למטה:")
    
    edited_cats_df = st.data_editor(
        cat_df,
        num_rows="dynamic",
        use_container_width=True,
        key="cat_editor",
        hide_index=True
    )
    
    if st.button("שמור קטגוריות", type="primary"):
        # Extract list
        new_cats_list = edited_cats_df["שם קטגוריה"].dropna().astype(str).tolist()
        # Remove duplicates and empty
        new_cats_list = sorted(list(set([c.strip() for c in new_cats_list if c.strip()])))
        
        save_categories(new_cats_list)
        st.success("הקטגוריות עודכנו בהצלחה!")
        st.rerun()
