import streamlit as st
import pandas as pd
import datetime
import calendar
import os
import plotly.graph_objects as go

# --- Sticky tab bar CSS ---
st.markdown(
    '''<style>
    div[role="tablist"] { position: sticky; top: 0; z-index: 1000; background-color: white; }
    </style>''', unsafe_allow_html=True)

# Define account fields including Depreciation Expense before Right of Use Assets Expense
ACCOUNT_FIELDS = [
    'Current Asset', 'Non Current Asset', 'Total Asset',
    'Current Liabilities', 'Non Current Liabilities', 'Total Liabilities',
    'Equity', 'Revenue', 'Administration Exp', 'Employee Expense',
    'Marketing Expense', 'Rent Expense', 'Depreciation Expense',
    'Right of Use Assets Expense', 'Total Operating Exp.', 'Operating Income',
    'Other Income and Expense', 'Net Income', 'Tax', 'Income After Tax'
]

# Data directory & file
DATA_DIR = 'data'
CSV_FILE = os.path.join(DATA_DIR, 'financial_data.csv')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Load or initialize DataFrame
def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=['Date'] + ACCOUNT_FIELDS)
    # Ensure columns
    for col in ['Date'] + ACCOUNT_FIELDS:
        if col not in df.columns:
            df[col] = 0
    # Type conversions
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    for f in ACCOUNT_FIELDS:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)
    return df

# Save/update row
def save_row(df, date, values):
    ts = pd.Timestamp(date)
    if (df['Date'] == ts).any():
        df.loc[df['Date'] == ts, ACCOUNT_FIELDS] = values
    else:
        row = {'Date': ts}
        row.update(dict(zip(ACCOUNT_FIELDS, values)))
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    return df

# Delete a date
def delete_date(df, date_str):
    ts = pd.Timestamp(date_str)
    df = df[df['Date'] != ts].reset_index(drop=True)
    df.to_csv(CSV_FILE, index=False)
    return df

# Format number for display
def fmt(x):
    if pd.isna(x): return ''
    return f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}"

# Main app
def main():
    df = load_data()
    st.session_state['data'] = df

    tab1, tab2, tab3 = st.tabs(['Input', 'Storage', 'Analysis'])

    # Tab 1: Input
    with tab1:
        st.header('Input Monthly Financial Data')
        with st.form('input_form', clear_on_submit=True):
            # Year and Month selectors
            current_year = datetime.date.today().year
            years = list(range(2000, current_year + 2))
            year = st.selectbox('Year', years, index=years.index(current_year))
            months = list(calendar.month_name)[1:]
            month = st.selectbox('Month', months, index=datetime.date.today().month - 1)
            month_idx = months.index(month) + 1
            # Account inputs
            inputs = [st.number_input(field, value=0.0, format='%.2f') for field in ACCOUNT_FIELDS]
            submitted = st.form_submit_button('Add')
            if submitted:
                last_day = calendar.monthrange(year, month_idx)[1]
                date = datetime.date(year, month_idx, last_day)
                df = save_row(st.session_state['data'], date, inputs)
                st.session_state['data'] = df
                st.success(f'Data saved for {month} {year}')

    # Tab 2: Storage
    with tab2:
        st.header('Stored Data (Pivot)')
        df = st.session_state['data']
        if df.empty:
            st.info('No data stored yet.')
        else:
            tmp = df.sort_values('Date').copy()
            tmp['DateStr'] = tmp['Date'].dt.strftime('%Y-%m-%d')
            piv = tmp.set_index('DateStr')[ACCOUNT_FIELDS].T.applymap(fmt)
            st.dataframe(piv, use_container_width=True)
            cols = st.columns(len(piv.columns))
            for i, d in enumerate(piv.columns):
                with cols[i]:
                    if st.button('???', key=f'del_{d}', help=f'Delete {d}'):
                        df = delete_date(st.session_state['data'], d)
                        st.session_state['data'] = df
                        st.success(f'Deleted data for {d}')

    # Tab 3: Analysis
    with tab3:
        st.header('Data Analysis')
        df = st.session_state['data']
        if df.empty:
            st.info('No data to analyze.')
        else:
            df_sorted = df.sort_values('Date')
            years = sorted(df_sorted['Date'].dt.year.unique())
            months = list(calendar.month_name)[1:]
            c1, c2 = st.columns(2)
            with c1:
                y1 = st.selectbox('From Year', years, index=0)
                m1 = st.selectbox('From Month', months, index=0)
            with c2:
                y2 = st.selectbox('To Year', years, index=len(years)-1)
                m2 = st.selectbox('To Month', months, index=len(months)-1)
            sd = datetime.date(y1, months.index(m1)+1, 1)
            ed_day = calendar.monthrange(y2, months.index(m2)+1)[1]
            ed = datetime.date(y2, months.index(m2)+1, ed_day)
            sel = df_sorted[(df_sorted['Date'] >= pd.Timestamp(sd)) & (df_sorted['Date'] <= pd.Timestamp(ed))].copy()
            sel['MonthYear'] = sel['Date'].dt.strftime('%b %Y')
            sel.set_index('MonthYear', inplace=True)

            st.subheader('Select Series to Plot')
            series = st.multiselect('Series', ACCOUNT_FIELDS, default=ACCOUNT_FIELDS)
            if series:
                fig = go.Figure()
                for s in series:
                    fig.add_trace(go.Scatter(
                        x=sel.index,
                        y=sel[s]/1e6,
                        mode='lines+markers',
                        name=s,
                        hovertemplate=f"{s}: %{{y:,.0f}} Mio<br>%{{x}}"
                    ))
                fig.update_layout(xaxis_title='Month-Year', yaxis_title='Amount (Million)')
                fig.update_yaxes(tickformat=',.0f', autorange=True)
                st.plotly_chart(fig, use_container_width=True)
                df_raw = sel[series].applymap(fmt).reset_index()
                df_raw.index += 1
                st.subheader('Raw Data Table')
                st.dataframe(df_raw, use_container_width=True)

            # Brokerage Ratios
            st.subheader('Brokerage Ratios')
            R = sel.copy()
            R['Liquidity Ratio'] = R['Current Asset'] / R['Current Liabilities']
            R['Leverage Ratio'] = R['Total Asset'] / R['Equity']
            R['Operating Margin (%)'] = R['Operating Income'] / R['Revenue'] * 100
            R['Efficiency Ratio (%)'] = R['Total Operating Exp.'] / R['Revenue'] * 100
            R['Return on Equity (%)'] = R['Net Income'] / R['Equity'] * 100
            R['Profit Margin (%)'] = R['Net Income'] / R['Revenue'] * 100
            R['After Tax Margin (%)'] = R['Income After Tax'] / R['Revenue'] * 100
            R['Tax Rate (%)'] = R['Tax'] / (R['Net Income'] + R['Tax']) * 100
            ratio_fields = ['Liquidity Ratio', 'Leverage Ratio', 'Operating Margin (%)', 'Efficiency Ratio (%)', 'Return on Equity (%)', 'Profit Margin (%)', 'After Tax Margin (%)', 'Tax Rate (%)']
            df_rat = R[ratio_fields].applymap(lambda x: f"{x:.2f}").reset_index()
            df_rat.index += 1
            st.dataframe(df_rat, use_container_width=True)

if __name__ == '__main__':
    main()
