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

# ACCOUNT FIELDS ORDER CORRECTION
ACCOUNT_FIELDS = [
    'Current Asset', 'Non Current Asset', 'Total Asset',
    'Current Liabilities', 'Non Current Liabilities', 'Total Liabilities',
    'Equity', 'Revenue', 'Administration Exp', 'Employee Expense',
    'Marketing Expense', 'Rent Expense',
    'Right of Use Assets Expense',  # right of use expense
    'Depreciation Expense',        # depreciation below ROU
    'Total Operating Exp.',
    'Operating Income', 'Other Income and Expense',
    'Net Income', 'Tax', 'Income After Tax'
]

# Data paths
data_dir = 'data'
csv_file = os.path.join(data_dir, 'financial_data.csv')
# Ensure data directory exists
os.makedirs(data_dir, exist_ok=True)

# Load data
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
else:
    df = pd.DataFrame(columns=['Date'] + ACCOUNT_FIELDS)
# Ensure columns exist
for c in ['Date'] + ACCOUNT_FIELDS:
    if c not in df.columns:
        df[c] = 0
# Convert types
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
for f in ACCOUNT_FIELDS:
    df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)
# Store in session
st.session_state['data'] = df

# Helpers
def save_row(df, date, vals):
    ts = pd.Timestamp(date)
    if (df['Date'] == ts).any():
        df.loc[df['Date'] == ts, ACCOUNT_FIELDS] = vals
    else:
        row = {'Date': ts}
        row.update(dict(zip(ACCOUNT_FIELDS, vals)))
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(csv_file, index=False)
    return df


def delete_date(df, date_str):
    ts = pd.Timestamp(date_str)
    df = df[df['Date'] != ts].reset_index(drop=True)
    df.to_csv(csv_file, index=False)
    return df


def fmt(x):
    if pd.isna(x): return ''
    return f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}"

# Main app

def main():
    df = st.session_state['data']
    # Precompute years list for input
    years = list(range(2000, datetime.date.today().year + 2))

    t1, t2, t3 = st.tabs(['Input', 'Storage', 'Analysis'])

    with t1:
        st.header('Input Data')
        with st.form('f1', clear_on_submit=True):
            year = st.selectbox('Year', years, index=len(years)-1)
            month = st.selectbox('Month', list(calendar.month_name)[1:], index=datetime.date.today().month-1)
            vals = [st.number_input(f, 0.0, format='%.2f') for f in ACCOUNT_FIELDS]
            if st.form_submit_button('Add'):
                last_day = calendar.monthrange(year, list(calendar.month_name).index(month))[1]
                d = datetime.date(year, list(calendar.month_name).index(month), last_day)
                df = save_row(df, d, vals)
                st.session_state['data'] = df
                st.success(f'Saved data for {month} {year}')

    with t2:
        st.header('Storage')
        df2 = df.sort_values('Date')
        if df2.empty:
            st.info('No data stored yet.')
        else:
            df2['DS'] = df2['Date'].dt.strftime('%Y-%m-%d')
            piv = df2.set_index('DS')[ACCOUNT_FIELDS].T.applymap(fmt)
            st.dataframe(piv, use_container_width=True)
            for i, ds in enumerate(piv.columns):
                if st.button(f'Delete {ds}', key=i):
                    df = delete_date(df, ds)
                    st.session_state['data'] = df
                    st.success(f'Deleted data for {ds}')

    with t3:
        st.header('Analysis')
        df3 = df.sort_values('Date')
        if df3.empty:
            st.info('No data to analyze.')
        else:
            yrs = sorted(df3['Date'].dt.year.unique())
            mos = list(calendar.month_name)[1:]
            c1, c2 = st.columns(2)
            with c1:
                y1 = st.selectbox('From Year', yrs, index=0)
                m1 = st.selectbox('From Month', mos, index=0)
            with c2:
                y2 = st.selectbox('To Year', yrs, index=len(yrs)-1)
                m2 = st.selectbox('To Month', mos, index=len(mos)-1)
            sd = datetime.date(y1, mos.index(m1)+1, 1)
            ed_day = calendar.monthrange(y2, mos.index(m2)+1)[1]
            ed = datetime.date(y2, mos.index(m2)+1, ed_day)
            sel = df3[(df3['Date'] >= sd) & (df3['Date'] <= ed)].copy()
            sel['MY'] = sel['Date'].dt.strftime('%b %Y')
            sel.set_index('MY', inplace=True)

            st.subheader('Select Series to Plot')
            series = st.multiselect('Series', ACCOUNT_FIELDS, default=ACCOUNT_FIELDS)
            if series:
                fig = go.Figure()
                for s in series:
                    fig.add_trace(go.Scatter(
                        x=sel.index,
                        y=sel[s] / 1e6,
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

    # Brokerage Ratios after chart (inside main indent)
    if not df3.empty:
        st.subheader('Brokerage Ratios')
        R = sel.copy()
        R['Liquidity Ratio']    = R['Current Asset'] / R['Current Liabilities']
        R['Leverage Ratio']     = R['Total Asset'] / R['Equity']
        R['Operating Margin (%)']  = R['Operating Income'] / R['Revenue'] * 100
        R['Efficiency Ratio (%)']  = R['Total Operating Exp.'] / R['Revenue'] * 100
        R['Return on Equity (%)']  = R['Net Income'] / R['Equity'] * 100
        R['Profit Margin (%)']      = R['Net Income'] / R['Revenue'] * 100
        R['After Tax Margin (%)']   = R['Income After Tax'] / R['Revenue'] * 100
        R['Tax Rate (%)']         = R['Tax'] / (R['Net Income'] + R['Tax']) * 100
        ratio_fields = [
            'Liquidity Ratio','Leverage Ratio','Operating Margin (%)',
            'Efficiency Ratio (%)','Return on Equity (%)','Profit Margin (%)',
            'After Tax Margin (%)','Tax Rate (%)'
        ]
        df_rat = R[ratio_fields].applymap(lambda x: f"{x:.2f}").reset_index()
        df_rat.index += 1
        st.dataframe(df_rat, use_container_width=True)

if __name__ == '__main__':
    main()
