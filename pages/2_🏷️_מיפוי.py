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
            st.switch_page("Home.py") 
else:
    # State management for index
    if 'mapping_index' not in st.session_state:
        st.session_state['mapping_index'] = 0
        
    current_idx = st.session_state['mapping_index']
    
    # Boundary check
    if current_idx >= len(to_map):
        st.session_state['mapping_index'] = 0
        current_idx = 0
        
    row = to_map.iloc[current_idx]
    
    # SPLIT LAYOUT: Right (Details) | Left (Buttons)
    # Streamlit columns are LTR. So col1 is Left, col2 is Right.
    # In RTL app, col1 appears on Right? NO. Streamlit columns order is strictly L-R in code structure.
    # CSS `flex-direction: row-reverse` might flip them visually if global RTL is on.
    # But usually `st.columns` renders structure.
    # User Request: "put... details on the right, in a narrow block, and sort all the categories buttons left to it"
    # So visually: [Buttons (Wide)] | [Details (Narrow)]
    # Code-wise (Assuming RTL Direction): Col 1 (Rightmost) | Col 2 (Leftmost)?
    # No, usually in RTL mode: Col 1 is Right side, Col 2 is Left side.
    # So `col_right, col_left = st.columns([1, 3])`
    
    c_right, c_left = st.columns([1, 3])
    
    with c_right:
        # Details Block
        st.info("פרטי עסקה")
        st.markdown(f"**תאריך:** {row['תאריך רכישה']}")
        st.markdown(f"**עסק:**")
        st.markdown(f"##### {row['שם בית עסק']}")
        st.markdown(f"**סכום:** {format_currency(row['סכום עסקה'])}")
        
        st.write("")
        st.write("")
        if st.button("⏭️ דלג הבא"):
            st.session_state['mapping_index'] += 1
            st.rerun()

    with c_left:
        st.subheader("בחר קטגוריה")
        categories = sorted(load_categories()) # Alphabetical sort
        valid_cats = [c for c in categories if c]
        
        # Grid for buttons
        cols = st.columns(4) 
        
        def save_category(cat):
            # 1. Update Expense
            original_idx = row.name
            df.at[original_idx, 'קטגוריה'] = cat
            save_expenses(df)
            
            # 2. Update Mapping (Learn/Overwrite)
            mapping = load_mapping()
            business = str(row['שם בית עסק']).strip()
            if business:
                mapping[business] = cat
                save_mapping(mapping)
            
            st.toast(f"סווג כ-{cat} ונשמר לאינדקס")
            # For "Next", we don't necessarily increment index, because current item disappears from 'to_map' logic
            # 'to_map' is recalculated. The item at 'current_idx' is now the *next* item.
            # So we keep index same? Or if we skipped previously, index might be > 0.
            # If we solve it, list shrinks. Index N becomes item N+1.
            # So generally keep index same, unless it's out of bounds.
            
            # However, if we preserve 'mapping_index' state, and the list shrank, 
            # we effectively move forward.
            # Reset index if unsafe.
            if st.session_state['mapping_index'] >= len(to_map) - 1:
                 st.session_state['mapping_index'] = 0
                 
            st.rerun()

        for i, cat in enumerate(valid_cats):
            with cols[i % 4]:
                if st.button(cat, use_container_width=True, key=f"btn_{i}"):
                    save_category(cat)
