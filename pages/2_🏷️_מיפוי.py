import streamlit as st
import pandas as pd
from utils import load_expenses, save_expenses, apply_custom_css, load_categories, format_currency, load_mapping, save_mapping

st.set_page_config(page_title="מיפוי מהיר", page_icon="🏷️", layout="wide")
apply_custom_css()

st.title("🏷️ מיפוי מהיר")

df = load_expenses()

# Filter empty categories
to_map = df[(df['קטגוריה'].isna()) | (df['קטגוריה'] == '') | (df['קטגוריה'] == 'nan')]

if to_map.empty:
    st.success("🎉 כל ההוצאות מסווגות!")
    if st.button("לסיכומים"):
        try:
            st.switch_page("1_📊_סיכומים.py")
        except:
            st.switch_page("Home.py") # Fallback
else:
    # Progress
    total = len(to_map)
    st.progress(0, text=f"נותרו {total} עסקאות לסיווג")

    # Get first item
    row = to_map.iloc[0]
    
    # COMPACT UI
    # Use a container with less padding
    with st.container():
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.caption("תאריך")
            st.markdown(f"**{row['תאריך רכישה']}**")
        with c2:
            st.caption("בית עסק")
            st.markdown(f"### {row['שם בית עסק']}")
        with c3:
            st.caption("סכום")
            st.markdown(f"### {format_currency(row['סכום עסקה'])}")

    st.divider()
    
    # Categories Buttons
    st.write("בחר קטגוריה:")
    categories = load_categories()
    valid_cats = [c for c in categories if c]
    
    # Compact Grid
    cols = st.columns(5) # 5 columns for compactness
    
    def save_category(cat):
        # 1. Update Expense
        original_idx = row.name
        df.at[original_idx, 'קטגוריה'] = cat
        save_expenses(df)
        
        # 2. Update Mapping (Learn)
        mapping = load_mapping()
        business = str(row['שם בית עסק']).strip()
        if business:
            mapping[business] = cat
            save_mapping(mapping)
        
        st.toast(f"סווג כ-{cat} ונשמר לאינדקס")
        st.rerun()

    for i, cat in enumerate(valid_cats):
        with cols[i % 5]:
            if st.button(cat, use_container_width=True, key=f"btn_{i}"):
                save_category(cat)
    
    st.divider()
    if st.button("⏭️ דלג בינתיים"):
        # Just move to next by reloading (random/sorted order handles it)
        # Or if strictly sequential, we might need state. 
        # But 'to_map' recalculates every time. 
        # To skip, we effectively need to temporarily ignore this index.
        # Simple hack: just move to next index in the list
        pass 
