import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from utils import load_expenses, get_latest_active_month, format_currency, apply_custom_css, COLORS, get_connection_status

# Page Config
st.set_page_config(page_title="סיכומים", page_icon="📊", layout="wide")

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
st.title("📊 סיכומים")
st.caption("מבט על ההוצאות והמגמות שלך")

if df.empty:
    st.info("אין נתונים להצגה. אנא עבור לדף ההגדרות והעלה קובץ נתונים.")
    # Show connection diagnostics
    status = get_connection_status()
    with st.expander("🔧 אבחון חיבור", expanded=True):
        st.write(f"**מחובר לסופאבייס:** {'✅ כן' if status['connected'] else '❌ לא'}")
        st.write(f"**כתובת:** {status['base_url']}")
        if status['error']:
            st.error(f"**שגיאה:** {status['error']}")
        else:
            st.write("אין שגיאות חיבור. ייתכן שמסד הנתונים ריק.")
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
        # Widget: Current Month vs Monthly Average
        # Calculate Average Monthly Spend (Last 12 Months)
        if not last_12_months.empty:
             avg_monthly = total_spend_12m / 12
        else:
             avg_monthly = 0

        # Calculate Current Month Spend
        current_month_data = df[df['חודש'] == active_month]
        current_spend = current_month_data['סכום עסקה'].sum() if not current_month_data.empty else 0
        
        # Calculate Delta (Percentage or Amount)
        delta_val = current_spend - avg_monthly
        delta_percent = (delta_val / avg_monthly * 100) if avg_monthly > 0 else 0
        
        st.metric(
            label="חודש נוכחי vs ממוצע",
            value=format_currency(current_spend),
            delta=f"{delta_percent:.1f}% ({format_currency(delta_val)})",
            delta_color="inverse" # Red if higher (bad), Green if lower (good)
        )

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
            x=alt.X('Month:T', title='חודש', axis=alt.Axis(format='%m/%Y', labelAngle=-45)),
        )
        
        # Line for Total
        line_total = base.mark_line(strokeWidth=4, color=COLORS['primary_dark']).encode(
            y=alt.Y('Amount', title='סכום'),
            tooltip=[
                alt.Tooltip('Month:T', title='חודש', format='%m/%Y'),
                alt.Tooltip('Type', title='סוג'),
                alt.Tooltip('Amount:Q', title='סכום', format=',.0f')
            ]
        )
        
        # Categories Line Chart
        chart_cat = alt.Chart(monthly_cat).mark_line(point=True).encode(
            x='Month:T',
            y='Amount',
            color=alt.Color('Category', legend=alt.Legend(title="קטגוריה")),
            tooltip=[
                alt.Tooltip('Month:T', title='חודש', format='%m/%Y'),
                alt.Tooltip('Category', title='קטגוריה'),
                alt.Tooltip('Amount:Q', title='סכום', format=',.0f')
            ]
        )
        
        # Total Average Line
        avg_line = alt.Chart(pd.DataFrame({'y': [avg_monthly_spend]})).mark_rule(strokeDash=[5, 5], color='gray', opacity=0.5).encode(
            y='y',
            tooltip=[alt.Tooltip('y', title='ממוצע שנתי', format=',.0f')]
        )

        # Combine
        final_chart = (chart_cat + line_total + avg_line).properties(height=450).interactive()
        
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
        # Exclude current year if requested? User said "Yearly Summary: Change Avg/Txn to Monthly Average (Total / 12)"
        # Showing all years is fine, but the metric should be Monthly Average.
        
        if years:
            selected_year = st.selectbox("בחר שנה להצגה", [int(y) for y in years], index=0)
            
            year_data = df[df['year'] == selected_year]
            
            # Group by Category
            cat_summary = year_data.groupby('קטגוריה')['סכום עסקה'].agg(['sum', 'count']).reset_index()
            cat_summary.columns = ['קטגוריה', 'סה"כ', 'מס׳ עסקאות']
            
            # Calculate Monthly Average (Total / 12)
            # Or Total / Number of active months in that year? usually /12 for annual budget view.
            # But for current incomplete year, it might be misleading.
            # Let's use 12 for past years, and current month count for this year?
            # Simpler: Total / 12 is a standard "Annualized Monthly Average".
            # If user wants "Real Average", they can look at the other table.
            # Let's stick to Total / 12 as requested implied by "Yearly" context usually.
            # Actually, better: if year == current year, divide by current month number?
            # Let's just do Total / 12 as a baseline for "Annual impact".
            
            months_in_year = 12
            if selected_year == datetime.now().year:
                months_in_year = max(1, datetime.now().month) # Avoid div by zero
            
            cat_summary['ממוצע חודשי'] = cat_summary['סה"כ'] / months_in_year
            
            cat_summary = cat_summary.sort_values('סה"כ', ascending=False)
            
            # Add Total Row
            total_sum = cat_summary['סה"כ'].sum()
            total_count = cat_summary['מס׳ עסקאות'].sum()
            total_avg = total_sum / months_in_year
            
            # Append Total using pd.concat
            total_row = pd.DataFrame([{
                'קטגוריה': '🛑 סה"כ', 
                'סה"כ': total_sum,
                'מס׳ עסקאות': total_count,
                'ממוצע חודשי': total_avg
            }])
            
            final_summary = pd.concat([cat_summary, total_row], ignore_index=True)
            
            st.dataframe(
                final_summary,
                column_config={
                    "קטגוריה": st.column_config.TextColumn("קטגוריה", width="medium"),
                    "סה\"כ": st.column_config.NumberColumn("סה\"כ שנתי", format="₪%.0f"),
                    "מס׳ עסקאות": st.column_config.NumberColumn("כמות", format="%d"),
                    "ממוצע חודשי": st.column_config.NumberColumn("ממוצע חודשי", format="₪%.0f"),
                },
                hide_index=True,
                use_container_width=True
            )
