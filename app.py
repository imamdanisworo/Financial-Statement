import streamlit as st
import pandas as pd
import datetime
import calendar
import os
import plotly.graph_objects as go
import time

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
    'Operating Profit Margin (%)': (lambda df: df['Operating Income'] / df['Revenue'].replace(0, pd.NA), 'percent'),
    'Net Profit Margin (%)': (lambda df: df['Net Income'] / df['Revenue'].replace(0, pd.NA), 'percent'),
    'Return on Assets (ROA) (%)': (lambda df: df['Net Income'] / df['Total Asset'].replace(0, pd.NA), 'percent'),
    'Return on Equity (ROE) (%)': (lambda df: df['Net Income'] / df['Equity'].replace(0, pd.NA), 'percent')
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

def save_data(df):
    df.to_csv(csv_file, index=False)

def delete_date(df, label_str):
    ts = pd.to_datetime(label_str, format='%b %Y')
    month = ts.month
    year = ts.year
    last_day = calendar.monthrange(year, month)[1]
    actual_date = pd.Timestamp(datetime.date(year, month, last_day))
    backup = df.copy()
    df = df[df['Date'] != actual_date].reset_index(drop=True)
    save_data(df)
    return df, backup

st.title("Financial Dashboard")
df = load_data()
if 'data' not in st.session_state:
    st.session_state['data'] = df
if 'backup' not in st.session_state:
    st.session_state['backup'] = None
if 'undo_timer' not in st.session_state:
    st.session_state['undo_timer'] = None
if 'rerun_flag' not in st.session_state:
    st.session_state['rerun_flag'] = False
if 'toast' not in st.session_state:
    st.session_state['toast'] = None

input_tab, storage_tab, analysis_tab = st.tabs(["Input", "Storage", "Analysis"])

with input_tab:
    st.header("Input Financial Data")
    with st.form("input_form", clear_on_submit=True):
        today = datetime.date.today()
        year = st.selectbox("Year", list(range(2000, today.year + 2)), index=list(range(2000, today.year + 2)).index(today.year))
        month = st.selectbox("Month", list(calendar.month_name)[1:], index=today.month - 1)
        inputs = [st.number_input(f, value=0.0, format="%.2f", step=0.1) for f in ACCOUNT_FIELDS]
        if st.form_submit_button("Save"):
            last_day = calendar.monthrange(year, list(calendar.month_name)[1:].index(month) + 1)[1]
            date = datetime.date(year, list(calendar.month_name)[1:].index(month) + 1, last_day)
            ts = pd.Timestamp(date)
            exists = (df['Date'] == ts).any()
            r = {'Date': ts}; r.update(dict(zip(ACCOUNT_FIELDS, inputs)))

            if exists:
                overwrite = st.checkbox(f"Data for {ts.strftime('%b %Y')} exists. Check to confirm overwrite.")
                if overwrite:
                    df = df[df['Date'] != ts]
                    df = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
                    save_data(df)
                    st.session_state['data'] = df
                    st.session_state['toast'] = "Data overwritten successfully."
                    st.session_state['rerun_flag'] = True
            else:
                df = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
                save_data(df)
                st.session_state['data'] = df
                st.session_state['toast'] = "Data saved successfully."
                st.session_state['rerun_flag'] = True

with storage_tab:
    st.header("Stored Financial Data (Editable)")
    st.caption("*All values are displayed in millions (Rp. Mio)*")
    df = st.session_state['data']
    df_sorted = df.sort_values("Date")
    if df_sorted.empty:
        st.info("No data available.")
    else:
        df_sorted['Month-Year'] = df_sorted['Date'].dt.strftime('%b %Y')
        pivot_df = df_sorted.set_index('Month-Year')[ACCOUNT_FIELDS].T
        pivot_df = pivot_df.applymap(lambda x: f"{round(x / 1e6):,}" if pd.notna(x) else '')

        st.subheader("Edit or Correct Financial Data")
        edited_df = st.data_editor(pivot_df, use_container_width=True, num_rows="dynamic")

        if st.button("Save Changes"):
            for month_year in edited_df.columns:
                dt = pd.to_datetime(month_year, format="%b %Y")
                last_day = calendar.monthrange(dt.year, dt.month)[1]
                actual_date = pd.Timestamp(datetime.date(dt.year, dt.month, last_day))
                for field in ACCOUNT_FIELDS:
                    try:
                        edited_val = float(str(edited_df.at[field, month_year]).replace(",", ""))
                        df.loc[df['Date'] == actual_date, field] = edited_val * 1e6
                    except:
                        pass
            save_data(df)
            st.session_state['data'] = df
            st.success("Changes saved successfully.")

        delete_target = st.selectbox("Select a period to delete:", pivot_df.columns.tolist())
        if st.button("Delete Selected"):
            df, backup = delete_date(df, delete_target)
            st.session_state['data'] = df
            st.session_state['backup'] = backup
            st.session_state['undo_timer'] = time.time()
            st.session_state['toast'] = f"Data for {delete_target} deleted."
            st.session_state['rerun_flag'] = True

        if st.session_state['backup'] is not None and st.session_state['undo_timer']:
            remaining = 10 - (time.time() - st.session_state['undo_timer'])
            if remaining > 0:
                st.info(f"You can undo delete in {int(remaining)} seconds.")
                if st.button("Undo Delete"):
                    st.session_state['data'] = st.session_state['backup']
                    save_data(st.session_state['backup'])
                    st.session_state['backup'] = None
                    st.session_state['undo_timer'] = None
                    st.session_state['toast'] = "Deletion undone."
                    st.session_state['rerun_flag'] = True
            else:
                st.session_state['backup'] = None
                st.session_state['undo_timer'] = None

if st.session_state.get('toast'):
    st.success(st.session_state['toast'])
    st.session_state['toast'] = None

if st.session_state.get('rerun_flag'):
    st.session_state['rerun_flag'] = False
    st.stop()
    st.experimental_rerun()

with analysis_tab:
    st.header("Financial Analysis")
    df = st.session_state['data']
    if df.empty:
        st.info("No data to analyze.")
    else:
        df['Label'] = df['Date'].dt.strftime('%b %Y')
        df.set_index('Label', inplace=True)

        selected = st.multiselect("Select Fields to Plot", ACCOUNT_FIELDS, default=[])
        if selected:
            fig = go.Figure()
            for f in selected:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df[f] / 1e6,
                    mode='lines+markers',
                    name=f,
                    hovertemplate=f"%{{x}}<br>{f}: Rp. %{{y:,.0f}} Mio<extra></extra>"
                ))
            fig.update_layout(
                title="Financial Trends (in Millions)",
                xaxis_title="Month-Year",
                yaxis=dict(tickformat=",.0f", tickprefix="Rp. "),
                legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center")
            )
            st.plotly_chart(fig, use_container_width=True)
            summary_table = (df[selected].T / 1e6).applymap(fmt)
            st.dataframe(summary_table, use_container_width=True)

        st.subheader("Financial Ratios")
        ratio_df = pd.DataFrame(index=df.index)
        for name, (func, _) in RATIO_FIELDS.items():
            ratio_df[name] = func(df)

        formatted_ratio_df = pd.DataFrame(index=ratio_df.index)
        for name, (_, typ) in RATIO_FIELDS.items():
            if typ == 'percent':
                formatted_ratio_df[name] = ratio_df[name].map(fmt_percent)
            else:
                formatted_ratio_df[name] = ratio_df[name].map(fmt_decimal)

        st.dataframe(formatted_ratio_df.T, use_container_width=True)
