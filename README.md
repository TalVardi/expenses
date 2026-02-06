# 💰 Expense Tracker (Hebrew RTL)

A personal expense tracking application built with Python and Streamlit, designed for Hebrew-speaking users with full RTL (Right-to-Left) support.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

## ✨ Features

- **📊 Dashboard**: Visual overview of expenses with charts and metrics
- **🏷️ Category Mapping**: Flashcard-style interface to categorize expenses
- **📋 All Expenses**: Searchable, filterable, editable expense table
- **⚙️ Settings**: Upload bank/credit card files, manage categories
- **🔄 RTL Layout**: Full Hebrew support with right-side navigation
- **📈 Smart Month Logic**: Automatically determines active month based on transaction volume

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/TalVardi/expenses.git
cd expenses
```

2. Create virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the app:
```bash
streamlit run Home.py
```

## 📁 Project Structure

```
expense-tracker/
├── Home.py                 # Main dashboard
├── utils.py               # Shared utilities, CSS, data functions
├── pages/
│   ├── 2_🏷️_מיפוי.py      # Category mapping
│   ├── 3_📋_כל_ההוצאות.py  # All expenses (with search)
│   └── 4_⚙️_הגדרות.py     # Settings
├── expenses.csv           # Data storage (gitignored)
├── categories.json        # Category list (gitignored)
└── requirements.txt
```

## 📝 Data Format

The app expects CSV/Excel files with the following columns:
- **תאריך רכישה** - Purchase date
- **שם בית עסק** - Business name
- **סכום עסקה** - Transaction amount
- **קטגוריה** - Category (optional)

## 🎨 Design

- Clean white/blue/cyan color palette
- Professional Hebrew typography (Rubik font)
- Modern card-based UI with subtle shadows
- Responsive sidebar navigation

---
*Built with ❤️ for personal finance tracking*
