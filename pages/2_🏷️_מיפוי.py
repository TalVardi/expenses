import streamlit as st
import pandas as pd
from utils import load_expenses, save_expenses, apply_custom_css, CATEGORIES, format_currency

st.set_page_config(page_title="מיפוי הוצאות", page_icon="🏷️", layout="wide")
apply_custom_css()

st.title("מיפוי הוצאות")
st.caption("סיווג מהיר של הוצאות ללא קטגוריה")

df = load_expenses()

# Filter empty categories
# Assuming empty string or NaN
to_map = df[(df['קטגוריה'].isna()) | (df['קטגוריה'] == '') | (df['קטגוריה'] == 'nan')]

if to_map.empty:
    st.success("🎉 כל ההוצאות מסווגות!")
    if st.button("חזרה לדאשבורד"):
        st.switch_page("Home.py")
else:
    st.markdown(f"**נותרו {len(to_map)} עסקאות לסיווג**")
    
    # "Flashcard" Mode - Show one at a time
    current_idx = st.session_state.get('mapping_index', 0)
    
    # Ensure index is valid
    if current_idx >= len(to_map):
        current_idx = 0
        
    row = to_map.iloc[current_idx]
    
    # Helper to save category
    def save_category(category):
        # Update the original dataframe
        # We need to find the specific row in the main df. 
        # Using index from to_map might be risky if df changed, but we loaded it fresh.
        # Ideally we have a unique ID. Date+Name+Amount is our "Key".
        
        original_idx = row.name  # Pandas preserves index
        df.at[original_idx, 'קטגוריה'] = category
        save_expenses(df)
        st.toast(f"סווג כ-{category}")
        # Next
        # We don't increment index because the current item is removed from 'to_map' on rerun
        # So we stay at 0 or move to next valid?
        # If we reload, 'to_map' shrinks. So index 0 is always the *next* one.
        st.rerun()

    # Card UI
    st.markdown(f"""
    <div class="metric-card" style="text-align: center; margin: 2rem 0; padding: 2rem;">
        <div style="font-size: 0.95rem; color: #718096; margin-bottom: 0.5rem;">{row['תאריך רכישה']}</div>
        <div style="font-size: 2rem; font-weight: 700; color: #0077B6; margin: 1rem 0;">{row['שם בית עסק']}</div>
        <div style="font-size: 1.5rem; color: #2D3748; font-weight: 500;">{format_currency(row['סכום עסקה'])}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### בחר קטגוריה:")
    
    # Buttons grid
    cols = st.columns(4)
    valid_cats = [c for c in CATEGORIES if c]
    
    for i, cat in enumerate(valid_cats):
        with cols[i % 4]:
            if st.button(cat, use_container_width=True, key=f"btn_{i}"):
                save_category(cat)
    
    # Skip / Delete
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⏭️ דלג בינתיים"):
            st.session_state['mapping_index'] = current_idx + 1
            st.rerun()
