import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime

# ============================================
# DESIGN SYSTEM - NEW CYAN/BLUE THEME
# ============================================
COLORS = {
    'background': '#FFFFFF',
    'card': '#F8F9FA',
    'primary': '#00B4D8',       # Bright Cyan
    'primary_dark': '#0077B6',  # Deep Blue
    'secondary': '#90E0EF',     # Light Cyan
    'accent': '#CAF0F8',        # Pale Cyan
    'success': '#48BB78',       # Green
    'warning': '#ED8936',       # Orange
    'danger': '#F56565',        # Red
    'text': '#2D3748',          # Dark Gray
    'text_muted': '#718096',    # Gray
    'border': '#E2E8F0',        # Light Gray Border
}

import json

# ============================================
# CONSTANTS & CONFIG
# ============================================
EXPENSES_FILE = "expenses.csv"
CATEGORIES_FILE = "categories.json"
COLUMNS = ['חודש', 'תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות']

DEFAULT_CATEGORIES = [
    'מזון וקניות בית',
    'אחזקת רכב',
    'דלק ונסיעות',
    'בילויים ויציאות משותפות',
    'קפה ואוכל בחוץ',
    'חשבונות דירה',
    'תקשורת',
    'חוגים ותחביבים',
    'ביטוחים ובריאות',
    'שונות'
]

def load_categories():
    """Load categories from JSON or return defaults."""
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CATEGORIES

def save_categories(categories_list):
    """Save categories to JSON."""
    with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(categories_list, f, ensure_ascii=False, indent=2)

# ============================================
# AUTO-CATEGORIZATION MAPPING
# ============================================
MAPPING_FILE = "mapping.json"

def load_mapping():
    """Load business-to-category mapping from JSON."""
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_mapping(mapping_dict):
    """Save business-to-category mapping to JSON."""
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping_dict, f, ensure_ascii=False, indent=2)

def auto_categorize_expenses(df, mapping):
    """
    Apply mapping to expenses dataframe.
    Only updates rows where 'קטגוריה' is empty, NaN, or None.
    """
    if df.empty or not mapping:
        return df
    
    # Ensure category column exists
    if 'קטגוריה' not in df.columns:
        df['קטגוריה'] = ''
        
    def get_category(row):
        # If category already exists, keep it
        current_cat = str(row.get('קטגוריה', '')).strip()
        if current_cat and current_cat.lower() != 'nan' and current_cat.lower() != 'none':
            return current_cat
        
        # Try to find match in mapping
        business_name = str(row.get('שם בית עסק', '')).strip()
        return mapping.get(business_name, '')

    df['קטגוריה'] = df.apply(get_category, axis=1)
    return df

CATEGORIES = load_categories()

# ============================================
# HELPER FUNCTIONS - DATA
# ============================================

def load_expenses() -> pd.DataFrame:
    """Load expenses from CSV file, create empty DataFrame if not exists."""
    try:
        df = pd.read_csv(EXPENSES_FILE, encoding='utf-8-sig')
        # Ensure all columns exist
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ''
        return df[COLUMNS]
    except FileNotFoundError:
        return pd.DataFrame(columns=COLUMNS)


def save_expenses(df: pd.DataFrame) -> None:
    """Save expenses DataFrame to CSV file."""
    df.to_csv(EXPENSES_FILE, index=False, encoding='utf-8-sig')


def format_currency(amount: float) -> str:
    """Format amount as Hebrew currency."""
    return f"₪{amount:,.0f}"


def get_current_month_str() -> str:
    return datetime.now().strftime('%m/%Y')


def normalize_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Read and normalize uploaded file to match main structure."""
    
    filename = uploaded_file.name.lower()
    all_records = []
    
    known_date_cols = ['תאריך רכישה', 'תאריך', 'תאריך עסקה']
    known_name_cols = ['שם בית עסק', 'שם בית העסק', 'עסק', 'שם העסק']
    known_amount_cols = ['סכום חיוב', 'סכום עסקה', 'סכום', 'סכום מקורי']
    summary_patterns = ['TOTAL FOR DATE', 'סך חיוב', 'סה"כ', 'סהכ', 'total']
    
    # Read file
    if filename.endswith('.csv'):
        try:
            df_raw = pd.read_csv(uploaded_file, encoding='utf-8-sig', header=None)
        except:
            uploaded_file.seek(0)
            df_raw = pd.read_csv(uploaded_file, encoding='utf-8', header=None)
    elif filename.endswith(('.xlsx', '.xls')):
        try:
            uploaded_file.seek(0)
            df_raw = pd.read_excel(uploaded_file, engine='openpyxl', header=None)
        except:
            try:
                uploaded_file.seek(0)
                df_raw = pd.read_excel(uploaded_file, engine='xlrd', header=None)
            except Exception as e:
                st.error(f"שגיאה בקריאת קובץ Excel: {str(e)}")
                return pd.DataFrame()
    else:
        st.error("סוג קובץ לא נתמך. אנא העלה קובץ CSV או Excel.")
        return pd.DataFrame()
    
    df_str = df_raw.astype(str)
    header_sections = []
    
    # Identify header rows by searching for known column names
    for row_idx in range(len(df_str)):
        row_values = df_str.iloc[row_idx].tolist()
        date_col = None
        name_col = None
        amount_col = None
        
        for col_idx, val in enumerate(row_values):
            val_clean = str(val).strip()
            if val_clean in known_date_cols:
                date_col = col_idx
            elif val_clean in known_name_cols:
                name_col = col_idx
            elif val_clean in known_amount_cols:
                amount_col = col_idx
        
        if date_col is not None and (name_col is not None or amount_col is not None):
            header_sections.append({
                'row': row_idx,
                'date_col': date_col,
                'name_col': name_col,
                'amount_col': amount_col
            })
    
    # Process sections
    for i, section in enumerate(header_sections):
        if i + 1 < len(header_sections):
            end_row = header_sections[i + 1]['row']
        else:
            end_row = len(df_raw)
        
        for row_idx in range(section['row'] + 1, end_row):
            row = df_raw.iloc[row_idx]
            
            date_val = row.iloc[section['date_col']] if section['date_col'] is not None else None
            name_val = row.iloc[section['name_col']] if section['name_col'] is not None else None
            amount_val = row.iloc[section['amount_col']] if section['amount_col'] is not None else None
            
            date_str = str(date_val).strip() if pd.notna(date_val) else ''
            name_str = str(name_val).strip() if pd.notna(name_val) else ''
            
            # Skip invalid rows
            if not date_str or date_str == 'nan' or not name_str or name_str == 'nan':
                continue
            
            # Skip summary rows
            if any(pattern.lower() in name_str.lower() for pattern in summary_patterns):
                continue
            
            # Parse amount
            try:
                amount_num = pd.to_numeric(amount_val, errors='coerce')
                if pd.isna(amount_num) or amount_num == 0:
                    continue
            except:
                continue
            
            all_records.append({
                'תאריך רכישה': date_str,
                'שם בית עסק': name_str,
                'סכום עסקה': amount_num,
                'חודש': '',
                'קטגוריה': '',
                'הערות': ''
            })
    
    if not all_records:
        return pd.DataFrame(columns=COLUMNS)
    
    normalized = pd.DataFrame(all_records, columns=COLUMNS)
    
    # Date processing
    def parse_date(date_val):
        if pd.isna(date_val):
            return None
        
        date_str = str(date_val).strip()
        formats_to_try = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y',
        ]
        
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        try:
            return pd.to_datetime(date_str, dayfirst=True)
        except:
            return None
    
    if len(normalized) > 0:
        parsed_dates = normalized['תאריך רכישה'].apply(parse_date)
        normalized['תאריך רכישה'] = parsed_dates.apply(lambda x: x.strftime('%Y-%m-%d') if x else '')
        normalized['חודש'] = parsed_dates.apply(lambda x: x.strftime('%m/%Y') if x else '')
    
    return normalized


def auto_categorize(new_df: pd.DataFrame, existing_df: pd.DataFrame) -> pd.DataFrame:
    """Auto-categorize new entries based on existing business names."""
    if existing_df.empty:
        return new_df
    
    business_category_map = {}
    # Prioritize most recent categorizations
    existing_sorted = existing_df.sort_values('תאריך רכישה', ascending=True)
    
    for _, row in existing_sorted.iterrows():
        business_name = str(row['שם בית עסק']).strip()
        category = str(row['קטגוריה']).strip()
        
        if business_name and category:
            business_category_map[business_name] = category
    
    def assign_category(row):
        if row['קטגוריה']:
            return row['קטגוריה']
        business_name = str(row['שם בית עסק']).strip()
        return business_category_map.get(business_name, '')
    
    new_df['קטגוריה'] = new_df.apply(assign_category, axis=1)
    return new_df


# ============================================
# CSS INJECTION
# ============================================

def get_latest_active_month(df: pd.DataFrame, min_transactions: int = 15) -> str:
    """
    Get the latest month that has at least `min_transactions`.
    Fallback to the actual last month in data if none meet criteria.
    If no data, return current month.
    """
    if df.empty or 'חודש' not in df.columns:
        return get_current_month_str()
        
    # Count per month
    counts = df['חודש'].value_counts()
    
    # Filter
    active_months = counts[counts >= min_transactions].index.tolist()
    
    if not active_months:
        # Fallback to absolute last month in data
        # Sort by date
        if 'תאריך רכישה' in df.columns:
            try:
                # Convert to datetime to find max
                temp_dates = pd.to_datetime(df['תאריך רכישה'], format='%Y-%m-%d', errors='coerce')
                latest_date = temp_dates.max()
                if pd.notna(latest_date):
                    return latest_date.strftime('%m/%Y')
            except:
                pass
        return get_current_month_str()
        
    # Parse months to sort correctly
    try:
        def parse_month(m):
            return datetime.strptime(m, '%m/%Y')
            
        sorted_active = sorted(active_months, key=parse_month, reverse=True)
        return sorted_active[0]
    except:
        return active_months[0]


# ============================================
# CSS INJECTION
# ============================================
def apply_custom_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700&display=swap');
        
        :root {{
            --primary: {COLORS['primary']};
            --primary-dark: {COLORS['primary_dark']};
            --secondary: {COLORS['secondary']};
            --accent: {COLORS['accent']};
            --background: {COLORS['background']};
            --card: {COLORS['card']};
            --text: {COLORS['text']};
            --text-muted: {COLORS['text_muted']};
            --border: {COLORS['border']};
        }}
        
        /* ============================================
           BASE STYLES
           ============================================ */
        .stApp {{
            background: linear-gradient(135deg, #F5F7FA 0%, #EBF4F8 100%);
            font-family: 'Rubik', sans-serif;
            color: var(--text);
        }}
        
        .stApp * {{
            font-family: 'Rubik', sans-serif;
        }}
        
        /* ============================================
           TYPOGRAPHY
           ============================================ */
        h1 {{
            color: var(--primary-dark) !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
            direction: rtl;
            text-align: right;
            margin-bottom: 0.5rem !important;
        }}
        
        h2, h3 {{
            color: var(--primary-dark) !important;
            font-weight: 600 !important;
            direction: rtl;
            text-align: right;
        }}
        
        h4, h5, h6 {{
            color: var(--text) !important;
            font-weight: 500;
            direction: rtl;
            text-align: right;
        }}
        
        p, span, label {{
            direction: rtl;
        }}
        
        /* ============================================
           RTL GLOBAL
           ============================================ */
        .element-container, .stMarkdown, .stDataFrame, .stAlert {{
            direction: rtl;
            text-align: right;
        }}
        
        /* ============================================
           SIDEBAR - RIGHT POSITIONED
           ============================================ */
        .stApp > div:first-child {{
            direction: rtl;
        }}
        
        section[data-testid="stSidebar"] {{
            position: fixed !important;
            right: 0 !important;
            left: auto !important;
            width: 260px !important;
            min-width: 260px !important;
            max-width: 260px !important;
            border-left: 1px solid var(--border);
            border-right: none;
            background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
            z-index: 999;
            box-shadow: -4px 0 12px rgba(0,0,0,0.03);
        }}
        
        section[data-testid="stSidebar"] > div {{
            direction: rtl;
            text-align: right;
            padding-top: 1rem;
        }}
        
        /* Main content area */
        .main .block-container {{
            max-width: calc(100% - 300px) !important;
            margin-right: auto !important;
            margin-left: 2rem !important;
            padding: 2rem !important;
        }}
        
        [data-testid="stAppViewContainer"] {{
            margin-right: 270px !important;
        }}
        
        /* Sidebar styling */
        div[data-testid="stSidebar"] * {{
            direction: rtl;
            text-align: right;
            color: var(--text) !important;
        }}
        
        /* Sidebar Nav */
        div[data-testid="stSidebarNav"] a {{
            direction: rtl;
            text-align: right;
            color: var(--text) !important;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin: 0.25rem 0.5rem;
            transition: all 0.2s ease;
        }}
        
        div[data-testid="stSidebarNav"] a:hover {{
            background-color: var(--accent) !important;
        }}
        
        [data-testid="stSidebarNavItems"] li {{
            direction: rtl;
        }}
        
        section[data-testid="stSidebar"] button[kind="header"] {{
            right: auto;
            left: 0;
        }}
        
        /* ============================================
           CARD COMPONENTS
           ============================================ */
        .metric-card {{
            background: #FFFFFF;
            padding: 1.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0, 119, 182, 0.06);
            border: 1px solid #E0F7FA;
            text-align: right;
            direction: rtl;
            transition: all 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 119, 182, 0.1);
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-dark);
            margin: 0.5rem 0;
        }}
        
        .metric-label {{
            font-size: 0.9rem;
            color: var(--text-muted);
            font-weight: 500;
        }}
        
        .metric-indicator {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        
        .metric-indicator.positive {{
            background: #E6FFFA;
            color: #047857;
        }}
        
        .metric-indicator.negative {{
            background: #FEF2F2;
            color: #DC2626;
        }}
        
        /* Default Streamlit Metrics */
        div[data-testid="stMetric"] {{
            background: #FFFFFF;
            padding: 1.25rem;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0, 119, 182, 0.06);
            border: 1px solid #E0F7FA;
            text-align: right;
            direction: rtl;
            transition: all 0.3s ease;
        }}
        
        div[data-testid="stMetric"]:hover {{
            box-shadow: 0 8px 20px rgba(0, 119, 182, 0.1);
        }}
        
        div[data-testid="stMetricLabel"] {{
            font-size: 0.9rem;
            color: var(--text-muted);
            font-weight: 500;
        }}
        
        div[data-testid="stMetricValue"] {{
            color: var(--primary-dark);
            font-weight: 700;
            font-size: 1.75rem;
        }}
        
        /* Section Cards */
        .section-card {{
            background: #FFFFFF;
            padding: 1.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0, 119, 182, 0.06);
            border: 1px solid #E0F7FA;
            margin-bottom: 1.5rem;
        }}
        
        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--primary-dark);
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid var(--accent);
        }}
        
        /* ============================================
           DATA TABLES
           ============================================ */
        [data-testid="stDataFrame"] {{
            border: none !important;
            background: #FFFFFF;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 119, 182, 0.06);
            overflow: hidden;
        }}
        
        [data-testid="stDataFrame"] [data-testid="StyledDataFrameDataGrid"] {{
            border: none !important;
        }}
        
        [data-testid="stDataFrame"] [role="columnheader"] {{
            background: linear-gradient(135deg, #E0F7FA 0%, #F0F9FF 100%) !important;
            color: var(--primary-dark) !important;
            font-weight: 600 !important;
            font-size: 14px;
            border-bottom: 2px solid var(--secondary) !important;
            padding: 0.75rem !important;
        }}
        
        [data-testid="stDataFrame"] [role="gridcell"] {{
            border-bottom: 1px solid #F0F4F8;
            color: var(--text);
            font-size: 14px;
            padding: 0.5rem !important;
        }}
        
        [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {{
            background-color: #FAFCFF !important;
        }}
        
        /* ============================================
           FORM ELEMENTS
           ============================================ */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stMultiselect > div > div {{
            border-radius: 10px !important;
            border: 1px solid var(--border) !important;
            background: #FFFFFF !important;
            direction: rtl;
            text-align: right;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(0, 180, 216, 0.15) !important;
        }}
        
        /* ============================================
           BUTTONS
           ============================================ */
        .stButton > button {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white !important;
            border-radius: 10px;
            border: none;
            padding: 0.6rem 1.5rem;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 180, 216, 0.3);
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 180, 216, 0.4);
        }}
        
        .stButton > button:active {{
            transform: translateY(0);
        }}
        
        /* Secondary Buttons */
        .stButton > button[kind="secondary"] {{
            background: #FFFFFF;
            color: var(--primary-dark) !important;
            border: 2px solid var(--primary);
            box-shadow: none;
        }}
        
        .stButton > button[kind="secondary"]:hover {{
            background: var(--accent);
        }}
        
        /* ============================================
           TABS
           ============================================ */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.5rem;
            background: transparent;
            border-bottom: 2px solid var(--border);
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            border-radius: 8px 8px 0 0;
            padding: 0.75rem 1.25rem;
            color: var(--text-muted);
            font-weight: 500;
            border: none;
        }}
        
        .stTabs [aria-selected="true"] {{
            background: var(--accent) !important;
            color: var(--primary-dark) !important;
            border-bottom: 3px solid var(--primary) !important;
        }}
        
        /* ============================================
           EXPANDERS
           ============================================ */
        .streamlit-expanderHeader {{
            background: #FFFFFF !important;
            border-radius: 10px !important;
            border: 1px solid var(--border) !important;
            font-weight: 500;
            color: var(--primary-dark) !important;
        }}
        
        .streamlit-expanderContent {{
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-top: none !important;
            border-radius: 0 0 10px 10px !important;
        }}
        
        /* ============================================
           ALERTS & MESSAGES
           ============================================ */
        .stAlert {{
            border-radius: 12px !important;
            border: none !important;
        }}
        
        div[data-testid="stNotification"] {{
            border-radius: 12px !important;
        }}
        
        /* Success */
        .stAlert[data-baseweb="notification"] {{
            background: linear-gradient(135deg, #E6FFFA 0%, #F0FFF4 100%) !important;
            border-right: 4px solid #10B981 !important;
        }}
        
        /* ============================================
           FILE UPLOADER
           ============================================ */
        [data-testid="stFileUploader"] {{
            background: #FFFFFF;
            border-radius: 12px;
            border: 2px dashed var(--secondary);
            padding: 1rem;
        }}
        
        [data-testid="stFileUploader"]:hover {{
            border-color: var(--primary);
            background: #FAFCFF;
        }}
        
        /* ============================================
           DIVIDERS
           ============================================ */
        hr {{
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border), transparent);
            margin: 1.5rem 0;
        }}
        
        /* ============================================
           CHARTS
           ============================================ */
        [data-testid="stVegaLiteChart"] {{
            background: #FFFFFF;
            border-radius: 16px;
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0, 119, 182, 0.06);
            border: 1px solid #E0F7FA;
        }}
        
        /* ============================================
           SCROLLBAR
           ============================================ */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #F5F7FA;
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--secondary);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--primary);
        }}
        
    </style>
    """, unsafe_allow_html=True)
