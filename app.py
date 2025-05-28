import streamlit as st
import pandas as pd
import datetime
import calendar
import os
import plotly.graph_objects as go

ACCOUNT_FIELDS = [
    'Current Asset', 'Non Current Asset', 'Total Asset',
    'Current Liabilities', 'Non Current Liabilities', 'Total Liabilities',
    'Equity', 'Revenue', 'Administration Exp', 'Employee Expense',
    'Marketing Expense', 'Rent Expense', 'Right of Use Assets Expense',
    'Depreciation Expense', 'Total Operating Exp.', 'Operating Income',
    'Other Income and Expense', 'Net Income', 'Tax', 'Income After Tax'
]

RATIO_FIELDS = {
    'Current Ratio': (lambda df: df['Current Asset'] / df['Current Liabilities'].replace(0, pd.NA), 'decimal'),
    'Debt to Equity Ratio': (lambda df: df['Total Liabilities'] / df['Equity'].replace(0, pd.NA), 'decimal'),
    'Operating Profit Margin': (lambda df: df['Operating Income'] / df['Revenue'].replace(0, pd.NA), 'percent'),
    'Net Profit Margin': (lambda df: df['Net Income'] / df['Revenue'].replace(0, pd.NA), 'percent'),
    'Return on Assets (ROA)': (lambda df: df['Net Income'] / df['Total Asset'].replace(0, pd.NA), 'percent'),
    'Return on Equity (ROE)': (lambda df: df['Net Income'] / df['Equity'].replace(0, pd.NA), 'percent')
}

csv_file = os.path.join('data', 'financial_data.csv')
os.makedirs('data', exist_ok=True)

fmt = lambda x: '' if pd.isna(x) else f"Rp. {int(x):,}" if float(x).is_integer() else f"Rp. {x:,.2f}"
fmt_decimal = lambda x: '' if pd.isna(x) else f"{x:.2f}"
fmt_percent = lambda x: '' if pd.isna(x) else f"{x*100:.2f}%"

def load_data():
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
    else:
        df = pd.DataFrame(columns=['Date'] + ACCOUNT_FIELDS)
    for col in ['Date'] + ACCOUNT_FIELDS:
        if col not in df.columns:
            df[col] = 0
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    for f in ACCOUNT_FIELDS:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)
    return df

def save_row(df, date, vals):
    ts = pd.Timestamp(date)
    if (df['Date'] == ts).any():
        st.warning(f"Data for {ts.date()} already exists and cannot be overwritten.")
        return df
    r = {'Date': ts}; r.update(dict(zip(ACCOUNT_FIELDS, vals)))
    df = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
    df.to_csv(csv_file, index=False)
    return df

def delete_date(df, date_str):
    ts = pd.Timestamp(date_str)
    df = df[df['Date'] != ts].reset_index(drop=True)
    df.to_csv(csv_file, index=False)
    return df

st.title("📊 Financial Dashboard")
df = load_data()
st.session_state['data'] = df
t1, t2, t3 = st.tabs(["📅 Input", "📂 Storage", "📊 Analysis"])

with t1:
    st.header("Input Financial Data")
    with st.form("input_form", clear_on_submit=True):
        today = datetime.date.today()
        year = st.selectbox("Year", list(range(2000, today.year + 2)), index=list(range(2000, today.year + 2)).index(today.year))
        month = st.selectbox("Month", list(calendar.month_name)[1:], index=today.month - 1)
        inputs = [st.number_input(f, value=0.0, format="%.2f") for f in ACCOUNT_FIELDS]
        if st.form_submit_button("Save"):
            last_day = calendar.monthrange(year, list(calendar.month_name)[1:].index(month) + 1)[1]
            date = datetime.date(year, list(calendar.month_name)[1:].index(month) + 1, last_day)
            df = save_row(df, date, inputs)
            st.session_state['data'] = df

with t2:
    st.header("Stored Financial Data (in Millions)")
    df_sorted = df.sort_values("Date")
    if df_sorted.empty:
        st.info("No data available.")
    else:
        df_sorted['Label'] = df_sorted['Date'].dt.strftime('%b %Y')
        display_df = df_sorted.set_index('Label')[ACCOUNT_FIELDS].T / 1e6
        st.dataframe(display_df.applymap(fmt), use_container_width=True)
        for d in display_df.columns:
            if st.button(f"Delete {d}", key=d):
                df = delete_date(df, pd.to_datetime(d))
                st.session_state['data'] = df
                st.experimental_rerun()

with t3:
    st.header("Financial Analysis")
    if df.empty:
        st.info("No data to analyze.")
    else:
        df['Label'] = df['Date'].dt.strftime('%b %Y')
        df.set_index('Label', inplace=True)

        selected = st.multiselect("Select Fields to Plot", ACCOUNT_FIELDS, default=['Revenue', 'Net Income'])
        if selected:
            fig = go.Figure()
            for f in selected:
                fig.add_trace(go.Scatter(x=df.index, y=df[f] / 1e6, mode='lines+markers', name=f))
            fig.update_layout(
                title="Financial Trends",
                xaxis_title="Month-Year",
                yaxis_title="Amount (in Millions)",
                legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center")
            )
            st.plotly_chart(fig, use_container_width=True)
            summary_table = (df[selected].T / 1e6).applymap(fmt)
            st.dataframe(summary_table, use_container_width=True)

        st.subheader("📊 Financial Ratios")
        ratio_df = pd.DataFrame(index=df.index)
        for name, (func, _) in RATIO_FIELDS.items():
            ratio_df[name] = func(df)
        ratio_table = ratio_df.T
        for name, (_, t) in RATIO_FIELDS.items():
            ratio_table.loc[name] = ratio_table.loc[name].map(fmt_percent if t == 'percent' else fmt_decimal)
        st.dataframe(ratio_table, use_container_width=True)
