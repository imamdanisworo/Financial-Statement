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

# Account fields
years = list(range(2000, datetime.date.today().year + 2))
ACCOUNT_FIELDS = [
    'Current Asset', 'Non Current Asset', 'Total Asset',
    'Current Liabilities', 'Non Current Liabilities', 'Total Liabilities',
    'Equity', 'Revenue', 'Administration Exp', 'Employee Expense',
    'Marketing Expense', 'Rent Expense', 'Right of Use Assets Expense',
    'Depreciation Expense', 'Total Operating Exp.', 'Operating Income',
    'Other Income and Expense', 'Net Income', 'Tax', 'Income After Tax'
]

# Financial ratios with formatting type
RATIO_FIELDS = {
    'Current Ratio': (lambda df: df['Current Asset'] / df['Current Liabilities'].replace(0, pd.NA), 'decimal'),
    'Debt to Equity Ratio': (lambda df: df['Total Liabilities'] / df['Equity'].replace(0, pd.NA), 'decimal'),
    'Operating Profit Margin': (lambda df: df['Operating Income'] / df['Revenue'].replace(0, pd.NA), 'percent'),
    'Net Profit Margin': (lambda df: df['Net Income'] / df['Revenue'].replace(0, pd.NA), 'percent'),
    'Return on Assets (ROA)': (lambda df: df['Net Income'] / df['Total Asset'].replace(0, pd.NA), 'percent'),
    'Return on Equity (ROE)': (lambda df: df['Net Income'] / df['Equity'].replace(0, pd.NA), 'percent')
}

# Paths
data_dir = 'data'
csv_file = os.path.join(data_dir, 'financial_data.csv')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Format helpers
fmt = lambda x: '' if pd.isna(x) else f"Rp. {int(x):,}" if float(x).is_integer() else f"Rp. {x:,.2f}"
fmt_decimal = lambda x: '' if pd.isna(x) else f"{x:.2f}"
fmt_percent = lambda x: '' if pd.isna(x) else f"{x*100:.2f}%"

# Load data
def load_data():
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
    else:
        df = pd.DataFrame(columns=['Date'] + ACCOUNT_FIELDS)
    for c in ['Date'] + ACCOUNT_FIELDS:
        if c not in df.columns:
            df[c] = 0
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    for f in ACCOUNT_FIELDS:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)
    return df

# Save row
def save_row(df, date, vals):
    ts = pd.Timestamp(date)
    if (df['Date'] == ts).any():
        df.loc[df['Date'] == ts, ACCOUNT_FIELDS] = vals
    else:
        r = {'Date': ts}
        r.update(dict(zip(ACCOUNT_FIELDS, vals)))
        df = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
    df.to_csv(csv_file, index=False)
    return df

# Delete date
def delete_date(df, date_str):
    ts = pd.Timestamp(date_str)
    df = df[df['Date'] != ts].reset_index(drop=True)
    df.to_csv(csv_file, index=False)
    return df

# Main app
def main():
    df = load_data()
    st.session_state['data'] = df
    t1, t2, t3 = st.tabs(['📅 Input', '📂 Storage', '📊 Analysis'])

    with t1:
        st.header('Input Financial Data')
        with st.form('f1', clear_on_submit=True):
            today = datetime.date.today()
            yr = st.selectbox('Year', years, index=years.index(today.year))
            mos = list(calendar.month_name)[1:]
            mo = st.selectbox('Month', mos, index=today.month - 1)
            vals = []

            for f in ACCOUNT_FIELDS:
                val = st.number_input(f, value=0.0, format="%.2f")
                st.caption(f"↳ {fmt(val)}")
                vals.append(val)

            if st.form_submit_button('Save Data'):
                day = calendar.monthrange(yr, mos.index(mo) + 1)[1]
                date = datetime.date(yr, mos.index(mo) + 1, day)
                df = save_row(st.session_state['data'], date, vals)
                st.session_state['data'] = df
                st.success(f"Data for {mo} {yr} saved successfully.")

    with t2:
        st.header('Stored Financial Data (in Millions)')
        df2 = st.session_state['data'].sort_values('Date')
        if df2.empty:
            st.info('No data available.')
        else:
            df2['DS'] = df2['Date'].dt.strftime('%Y-%m-%d')
            piv = df2.set_index('DS')[ACCOUNT_FIELDS].T.astype(float) / 1e6
            piv_display = piv.applymap(fmt)
            st.dataframe(piv_display, use_container_width=True)
            for d in piv.columns:
    if st.button(f'🗑️ Delete {d}', key=f'del_{d}'):
        df2 = delete_date(st.session_state['data'], d)
        st.session_state['data'] = df2
        st.success(f"Deleted entry for {d}.")

    with t3:
        st.header('Data Analysis')
        df3 = st.session_state['data'].sort_values('Date')
        if df3.empty:
            st.info('No data available.')
        else:
            yrs = sorted(df3['Date'].dt.year.unique())
            mos = list(calendar.month_name)[1:]
            c1, c2 = st.columns(2)
            with c1:
                y1 = st.selectbox('From Year', yrs)
                m1 = st.selectbox('From Month', mos)
            with c2:
                y2 = st.selectbox('To Year', yrs, index=len(yrs) - 1)
                m2 = st.selectbox('To Month', mos, index=len(mos) - 1)
            sd = pd.Timestamp(datetime.date(y1, mos.index(m1) + 1, 1))
            ed = pd.Timestamp(datetime.date(y2, mos.index(m2) + 1, calendar.monthrange(y2, mos.index(m2) + 1)[1]))
            sel = df3[(df3['Date'] >= sd) & (df3['Date'] <= ed)].copy()
            sel['MY'] = sel['Date'].dt.strftime('%b %Y')
            sel.set_index('MY', inplace=True)

            series = st.multiselect('Select Series to Analyze', ACCOUNT_FIELDS, ACCOUNT_FIELDS)
            if series:
                st.subheader('Trend Chart (in Millions)')
                fig = go.Figure()
                for f in series:
                    fig.add_trace(go.Scatter(x=sel.index, y=sel[f] / 1e6, mode='lines+markers', name=f))
                fig.update_layout(
                    title='Financial Series Trend',
                    xaxis_title='Month-Year',
                    yaxis_title='Amount (in Millions)',
                    margin=dict(l=40, r=40, t=60, b=40),
                    height=400,
                    legend=dict(orientation='v', yanchor='top', y=1, xanchor='right', x=1)
                )
                fig.update_yaxes(tickformat=',.0f', autorange=True)
                st.plotly_chart(fig, use_container_width=True)

                st.subheader('Summary Table (in Millions)')
                table = (sel[series].T / 1e6).applymap(fmt)
                st.dataframe(table, use_container_width=True, height=int(32 * (len(table.index) + 1)))

            st.subheader('Financial Ratios')
            ratio_df = pd.DataFrame(index=sel.index)
            for name, (func, _) in RATIO_FIELDS.items():
                ratio_df[name] = func(sel)

            ratio_table = ratio_df.T
            for name, (_, ftype) in RATIO_FIELDS.items():
                if ftype == 'percent':
                    ratio_table.loc[name] = ratio_table.loc[name].map(fmt_percent)
                else:
                    ratio_table.loc[name] = ratio_table.loc[name].map(fmt_decimal)

            st.dataframe(ratio_table, use_container_width=True, height=int(32 * (len(ratio_table.index) + 1)))

if __name__ == '__main__':
    main()
