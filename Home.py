import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from utils import load_expenses, get_latest_active_month, format_currency, apply_custom_css, COLORS

# Page Config
st.set_page_config(page_title="דאשבורד פיננסי", page_icon="🏠", layout="wide")

# Apply Global CSS
apply_custom_css()

# Load Data
df = load_expenses()

# Helper for date sorting
if not df.empty and 'תאריך רכישה' in df.columns:
    df['date_dt'] = pd.to_datetime(df['תאריך רכישה'], errors='coerce')
    df['year'] = df['date_dt'].dt.year
    df['month_dt'] = df['date_dt'].dt.to_period('M')

# Header
st.title("דאשבורד פיננסי")
st.caption("סקירה כללית של ההוצאות שלך")

if df.empty:
    st.info("אין נתונים להצגה. אנא עבור לדף ההגדרות והעלה קובץ נתונים.")
else:
    # ---------------------------------------------------------
    # TOP METRICS (Averages and Totals)
    # ---------------------------------------------------------
    # Determine "Current" Month (Smart Logic)
    active_month = get_latest_active_month(df)
    
    # Filter last 12 months based on REAL time, or based on ACTIVE month?
    # Usually "Last 12 months" means "Historical context".
    # Let's keep 12 months from NOW for the trend, but highlight the ACTIVE month in metrics.
    
    now = datetime.now()
    # Ensure correct type for filtering
    last_12_months = df[df['date_dt'] >= (pd.Timestamp(now) - pd.DateOffset(months=12))]
    
    total_spend_12m = last_12_months['סכום עסקה'].sum()
    avg_monthly_spend = total_spend_12m / 12  # Simple avg
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("סך הוצאות (12 חודשים)", format_currency(total_spend_12m))
    with col2:
        st.metric("ממוצע חודשי", format_currency(avg_monthly_spend))
    with col3:
        curr_month_spend = df[df['חודש'] == active_month]['סכום עסקה'].sum()
        st.metric(f"חודש פעיל ({active_month})", format_currency(curr_month_spend))
    with col4:
        # Most expensive category avg
        cat_stats = last_12_months.groupby('קטגוריה')['סכום עסקה'].sum().sort_values(ascending=False)
        if not cat_stats.empty:
            top_cat = cat_stats.index[0]
            st.metric(f"הכי בזבזני: {top_cat}", format_currency(cat_stats.iloc[0]))

    st.markdown("---")

    # ---------------------------------------------------------
    # MAIN CHART: LINE GRAPH (Total + Categories)
    # ---------------------------------------------------------
    st.markdown("### מגמות הוצאות (12 חודשים אחרונים)")
    
    if not last_12_months.empty:
        # Monthly totals
        monthly_total = last_12_months.groupby(last_12_months['date_dt'].dt.strftime('%Y-%m'))['סכום עסקה'].sum().reset_index()
        monthly_total.columns = ['Month', 'Amount']
        monthly_total['Type'] = 'סה"כ'
        
        # Category totals per month
        monthly_cat = last_12_months.groupby([last_12_months['date_dt'].dt.strftime('%Y-%m'), 'קטגוריה'])['סכום עסקה'].sum().reset_index()
        monthly_cat.columns = ['Month', 'Category', 'Amount']
        
        # Base Chart
        base = alt.Chart(monthly_total).encode(
            x=alt.X('Month:T', title='חודש', axis=alt.Axis(format='%Y-%m')),
            tooltip=['Month', 'Amount']
        )
        
        # Line for Total
        line_total = base.mark_line(strokeWidth=4, color=COLORS['primary_dark']).encode(
            y=alt.Y('Amount', title='סכום'),
            tooltip=['Month', 'Amount']
        )
        
        # Stacked Area/Lines for categories? Keeping it simple with multiline might be messy.
        # User asked for: "line graph with all the categories we have... make a line for a total expenses as well."
        
        chart_cat = alt.Chart(monthly_cat).mark_line(point=True).encode(
            x='Month:T',
            y='Amount',
            color='Category',
            tooltip=['Month', 'Category', 'Amount']
        )
        
        # Combine
        final_chart = (chart_cat + line_total).properties(height=400).interactive()
        
        st.altair_chart(final_chart, use_container_width=True)

    # ---------------------------------------------------------
    # AVERAGES & YEARLY SUMMARIES
    # ---------------------------------------------------------
    row2_col1, row2_col2 = st.columns([1, 2])
    
    with row2_col1:
        st.markdown("### ממוצעים לקטגוריה")
        if not last_12_months.empty:
            avg_per_cat = last_12_months.groupby('קטגוריה')['סכום עסקה'].mean().reset_index()
            avg_per_cat = avg_per_cat.sort_values('סכום עסקה', ascending=False)
            
            st.dataframe(
                avg_per_cat,
                column_config={
                    "קטגוריה": "קטגוריה",
                    "סכום עסקה": st.column_config.NumberColumn("ממוצע", format="₪%.0f")
                },
                hide_index=True,
                use_container_width=True
            )


    with row2_col2:
        st.markdown("### סיכום שנתי לפי קטגוריות")
        
        years = sorted(df['year'].dropna().unique(), reverse=True)
        if years:
            selected_year = st.selectbox("בחר שנה להצגה", [int(y) for y in years], index=0)
            
            year_data = df[df['year'] == selected_year]
            
            # Group by Category
            cat_summary = year_data.groupby('קטגוריה')['סכום עסקה'].agg(['sum', 'count', 'mean']).reset_index()
            cat_summary.columns = ['קטגוריה', 'סה"כ', 'מס׳ עסקאות', 'ממוצע לעסקה']
            cat_summary = cat_summary.sort_values('סה"כ', ascending=False)
            
            # Add Total Row
            total_sum = cat_summary['סה"כ'].sum()
            total_count = cat_summary['מס׳ עסקאות'].sum()
            total_avg = total_sum / total_count if total_count > 0 else 0
            
            # Append Total using pd.concat
            total_row = pd.DataFrame([{
                'קטגוריה': '🛑 סה"כ', # Using emoji to make it distinct/sortable or just visually last?
                'סה"כ': total_sum,
                'מס׳ עסקאות': total_count,
                'ממוצע לעסקה': total_avg
            }])
            
            final_summary = pd.concat([cat_summary, total_row], ignore_index=True)
            
            st.dataframe(
                final_summary,
                column_config={
                    "קטגוריה": st.column_config.TextColumn("קטגוריה", width="medium"),
                    "סה\"כ": st.column_config.NumberColumn("סה\"כ שנתי", format="₪%.0f"),
                    "מס׳ עסקאות": st.column_config.NumberColumn("כמות", format="%d"),
                    "ממוצע לעסקה": st.column_config.NumberColumn("ממוצע לעסקה", format="₪%.0f"),
                },
                hide_index=True,
                use_container_width=True
            )
