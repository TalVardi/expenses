import streamlit as st
import pandas as pd
import os
import re
import time
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

# Constants
EXPENSES_FILE = "expenses.csv"
CATEGORIES_FILE = "categories.json"
MAPPING_FILE = "mapping.json"

COLUMNS = ['חודש', 'תאריך רכישה', 'שם בית עסק', 'סכום עסקה', 'קטגוריה', 'הערות']

DEFAULT_CATEGORIES = [
    "אוכל", "סופר", "דלק", "חשבונות", "ביטוח", 
    "משכנתא/שכירות", "חינוך", "פנאי", "בגדים", 
    "תחבורה", "בריאות", "אחר"
]

import json
import requests

# ============================================
# RETRY / TIMEOUT SETTINGS
# ============================================
MAX_RETRIES = 3
RETRY_DELAY = 1   # seconds (multiplied by attempt number)
REQUEST_TIMEOUT = 10  # seconds

# ============================================
# SUPABASE CONNECTOR (VIA REST API)
# ============================================
class SupabaseConnector:
    def __init__(self):
        self.base_url = ""
        self.headers = {}
        self.connected = False
        self.connection_error = None
        self._connect()

    def _connect(self):
        try:
            if "supabase" in st.secrets:
                self.base_url = st.secrets["supabase"]["SUPABASE_URL"]
                key = st.secrets["supabase"]["SUPABASE_KEY"]
                self.headers = {
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                }
                self.connected = True
            else:
                self.connection_error = "No 'supabase' section in st.secrets"
        except Exception as e:
            self.connection_error = str(e)
            st.warning(f"⚠️ שגיאת חיבור למסד נתונים: {e}")

    def _request_with_retry(self, method, url, **kwargs):
        """Make an HTTP request with retry logic and timeout."""
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        kwargs.setdefault('headers', self.headers)
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = method(url, **kwargs)
                if response.status_code in (200, 201, 204):
                    return response
                # Non-success status — retry on server errors (5xx)
                if response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                # Client error or final attempt — return as-is
                return response
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                raise
        return None  # Should not reach here

    # --- EXPENSES ---
    def load_expenses(self):
        if self.connected:
            for attempt in range(MAX_RETRIES):
                try:
                    url = f"{self.base_url}/rest/v1/expenses?select=*"
                    all_data = []
                    offset = 0
                    limit = 1000
                    fetch_error = False
                    
                    while True:
                        paged_url = f"{url}&limit={limit}&offset={offset}"
                        response = self._request_with_retry(requests.get, paged_url)

                        if response is not None and response.status_code == 200:
                            data = response.json()
                            if not data:
                                break
                            all_data.extend(data)
                            
                            if len(data) < limit:
                                break
                            
                            offset += limit
                        else:
                            status = response.status_code if response else 'No response'
                            fetch_error = True
                            break
                    
                    if fetch_error:
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY * (attempt + 1))
                            continue
                        st.warning(f"⚠️ שגיאה בטעינת הוצאות מהשרת (סטטוס: {status}). מנסה מקור מקומי.")
                        break
                    
                    if all_data:
                        df = pd.DataFrame(all_data)
                        
                        if not df.empty:
                            rename_map = {
                                'date': 'תאריך רכישה',
                                'business': 'שם בית עסק',
                                'amount': 'סכום עסקה',
                                'category': 'קטגוריה',
                                'notes': 'הערות',
                                'month': 'חודש',
                                'id': 'id'
                            }
                            df = df.rename(columns=rename_map)
                            df.replace(['None', 'nan', 'NONE', 'NaN'], '', inplace=True)
                            
                            for col in COLUMNS:
                                if col not in df.columns:
                                    df[col] = ''
                            
                            cols_to_return = COLUMNS + ['id'] if 'id' in df.columns else COLUMNS
                            return df[cols_to_return]
                    
                    if not all_data:
                         return pd.DataFrame(columns=COLUMNS)

                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    st.warning(f"⚠️ לא ניתן לטעון הוצאות מהשרת: {e}")
                    break
        return self._load_local_expenses()

    def save_expenses(self, df):
        if self.connected:
            try:
                records = []
                for _, row in df.iterrows():
                    def safe_str(val):
                        if pd.isna(val) or val is None or str(val).lower() == 'nan' or str(val).lower() == 'none':
                            return ''
                        return str(val).strip()
                    
                    def safe_float(val):
                        try:
                            return float(val)
                        except:
                            return 0.0

                    records.append({
                        'date': safe_str(row.get('תאריך רכישה')),
                        'business': safe_str(row.get('שם בית עסק')),
                        'amount': safe_float(row.get('סכום עסקה')),
                        'category': safe_str(row.get('קטגוריה')),
                        'notes': safe_str(row.get('הערות')),
                        'month': safe_str(row.get('חודש'))
                    })
                
                url = f"{self.base_url}/rest/v1/expenses"
                try:
                    self._request_with_retry(requests.delete, f"{url}?id=neq.0")
                except Exception:
                    pass

                chunk_size = 1000
                for i in range(0, len(records), chunk_size):
                    chunk = records[i:i + chunk_size]
                    self._request_with_retry(requests.post, url, json=chunk)
                    
                return
            except Exception as e:
                st.warning(f"⚠️ שגיאה בשמירת הוצאות: {e}")
        self._save_local_expenses(df)

    # --- CATEGORIES ---
    def load_categories(self):
        if self.connected:
            for attempt in range(MAX_RETRIES):
                try:
                    url = f"{self.base_url}/rest/v1/categories?select=name"
                    all_data = []
                    offset = 0
                    limit = 1000
                    
                    while True:
                        paged_url = f"{url}&limit={limit}&offset={offset}"
                        response = self._request_with_retry(requests.get, paged_url)
                        if response is not None and response.status_code == 200:
                            data = response.json()
                            if not data:
                                break
                            all_data.extend(data)
                            if len(data) < limit:
                                break
                            offset += limit
                        else:
                            break
                    
                    if all_data:
                        return [item['name'] for item in all_data]
                    return self._load_local_categories()
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    st.warning(f"⚠️ לא ניתן לטעון קטגוריות מהשרת: {e}")
                    break
        return self._load_local_categories()

    def save_categories(self, categories_list):
        if self.connected:
            try:
                url = f"{self.base_url}/rest/v1/categories"
                self._request_with_retry(requests.delete, f"{url}?name=neq.PLACEHOLDER")
                
                data = [{'name': c} for c in categories_list]
                self._request_with_retry(requests.post, url, json=data)
                return
            except Exception as e:
                st.warning(f"⚠️ שגיאה בשמירת קטגוריות: {e}")
        self._save_local_categories(categories_list)

    # --- MAPPING ---
    def load_mapping(self):
        if self.connected:
            for attempt in range(MAX_RETRIES):
                try:
                    url = f"{self.base_url}/rest/v1/mapping?select=*"
                    all_data = []
                    offset = 0
                    limit = 1000
                    
                    while True:
                        paged_url = f"{url}&limit={limit}&offset={offset}"
                        response = self._request_with_retry(requests.get, paged_url)
                        if response is not None and response.status_code == 200:
                            data = response.json()
                            if not data:
                                break
                            all_data.extend(data)
                            if len(data) < limit:
                                break
                            offset += limit
                        else:
                            break

                    if all_data:
                        mapping = {}
                        for r in all_data:
                            b = str(r.get('business', '')).strip()
                            c = str(r.get('category', '')).strip()
                            if b and c:
                                mapping[b] = c
                        return mapping
                    return self._load_local_mapping()
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    st.warning(f"⚠️ לא ניתן לטעון מיפויים מהשרת: {e}")
                    break
        return self._load_local_mapping()

    def save_mapping(self, mapping_dict):
        if self.connected:
            try:
                url = f"{self.base_url}/rest/v1/mapping"
                self._request_with_retry(requests.delete, f"{url}?business=neq.PLACEHOLDER")
                
                data = [{'business': k, 'category': v} for k, v in mapping_dict.items()]
                
                chunk_size = 1000
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i + chunk_size]
                    self._request_with_retry(requests.post, url, json=chunk)
                return
            except Exception as e:
                st.warning(f"⚠️ שגיאה בשמירת מיפויים: {e}")
        self._save_local_mapping(mapping_dict)


    # --- LOCAL FALLBACKS ---
    def _load_local_expenses(self):
        try:
            df = pd.read_csv(EXPENSES_FILE, encoding='utf-8-sig')
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df[COLUMNS]
        except FileNotFoundError:
            return pd.DataFrame(columns=COLUMNS)

    def _save_local_expenses(self, df):
        df.to_csv(EXPENSES_FILE, index=False, encoding='utf-8-sig')

    def _load_local_categories(self):
        if os.path.exists(CATEGORIES_FILE):
            try:
                with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return DEFAULT_CATEGORIES

    def _save_local_categories(self, categories_list):
        with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(categories_list, f, ensure_ascii=False, indent=2)

    def _load_local_mapping(self):
        if os.path.exists(MAPPING_FILE):
            try:
                with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_local_mapping(self, mapping_dict):
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping_dict, f, ensure_ascii=False, indent=2)


# Initialize Global Connector
# NOTE: Removed @st.cache_resource because it can cache failed/None states
# and cause persistent "no data" issues after Streamlit Cloud wake-up.
def _get_connector():
    try:
        return SupabaseConnector()
    except Exception as e:
        print(f"[CRITICAL] Failed to create SupabaseConnector: {e}")
        return None

db = _get_connector()


# ============================================
# DATA ACCESS FUNCTIONS (WRAPPERS)
# ============================================
def load_categories():
    if db is None:
        return []
    return db.load_categories()

def save_categories(categories_list):
    if db is None:
        return
    db.save_categories(categories_list)

def load_mapping():
    if db is None:
        return {}
    return db.load_mapping()

def save_mapping(mapping_dict):
    if db is None:
        return
    db.save_mapping(mapping_dict)

def load_expenses() -> pd.DataFrame:
    if db is None:
        return pd.DataFrame(columns=COLUMNS)
    return db.load_expenses()

def get_connection_status():
    """Return connection status info for diagnostics."""
    if db is None:
        return {
            'connected': False,
            'error': 'SupabaseConnector failed to initialize (db is None). Check logs.',
            'base_url': 'N/A'
        }
    return {
        'connected': db.connected,
        'error': db.connection_error,
        'base_url': db.base_url[:30] + '...' if db.base_url else 'N/A'
    }

def save_expenses(df: pd.DataFrame) -> None:
    if db is None:
        return
    db.save_expenses(df)


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


def auto_categorize_expenses(new_df: pd.DataFrame, existing_df: pd.DataFrame) -> pd.DataFrame:
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

def get_latest_active_month(df, min_transactions=20):
    """
    Get the latest month that has at least `min_transactions`.
    Fallback to the actual last month in data if none meet criteria.
    If no data, return current month.
    """
    if df.empty or 'חודש' not in df.columns:
        return datetime.now().strftime('%m/%Y')
        
    # Count per month
    counts = df['חודש'].value_counts()
    
    # Filter months with enough transactions
    active_months = counts[counts >= min_transactions].index.tolist()
    
    def parse_month(m):
        try:
            return datetime.strptime(m, '%m/%Y')
        except:
            return datetime.min

    if not active_months:
        # Fallback to absolute last month in data (based on date column)
        if 'תאריך רכישה' in df.columns:
            try:
                # Convert to datetime to find max
                temp_dates = pd.to_datetime(df['תאריך רכישה'], format='%Y-%m-%d', errors='coerce')
                latest_date = temp_dates.max()
                if pd.notna(latest_date):
                    return latest_date.strftime('%m/%Y')
            except:
                pass
        
        # Fallback to sorting 'Month' strings if date column fails
        all_months = df['חודש'].unique().tolist()
        if all_months:
             sorted_all = sorted(all_months, key=parse_month, reverse=True)
             return sorted_all[0]
             
        return datetime.now().strftime('%m/%Y')
        
    # Sort active months to get the latest one
    sorted_active = sorted(active_months, key=parse_month, reverse=True)
    return sorted_active[0]


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
