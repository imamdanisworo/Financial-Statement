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

# Paths
data_dir = 'data'
csv_file = os.path.join(data_dir, 'financial_data.csv')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

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

# Format helper
fmt = lambda x: '' if pd.isna(x) else (f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}")

# Main app
def main():
    df = load_data()
    st.session_state['data'] = df
    t1, t2, t3 = st.tabs(['Input', 'Storage', 'Analysis'])

    with t1:
        st.header('Input Data')
        with st.form('f1', clear_on_submit=True):
            yr = st.selectbox('Year', years, index=len(years) - 1)
            mos = list(calendar.month_name)[1:]
            mo = st.selectbox('Month', mos, index=datetime.date.today().month - 1)
            vals = [st.number_input(f, format="%.2f", value=0.0) for f in ACCOUNT_FIELDS]
            if st.form_submit_button('Add'):
                day = calendar.monthrange(yr, mos.index(mo) + 1)[1]
                date = datetime.date(yr, mos.index(mo) + 1, day)
                df = save_row(st.session_state['data'], date, vals)
                st.session_state['data'] = df
                st.success('Saved')

    with t2:
        st.header('Stored Data')
        df2 = st.session_state['data'].sort_values('Date')
        if df2.empty:
            st.info('No data')
        else:
            df2['DS'] = df2['Date'].dt.strftime('%Y-%m-%d')
            piv = df2.set_index('DS')[ACCOUNT_FIELDS].T.astype(float)
            st.dataframe(piv, use_container_width=True)
            for d in piv.columns:
                if st.button(f'Del {d}'):
                    df2 = delete_date(st.session_state['data'], d)
                    st.session_state['data'] = df2
                    st.success('Deleted')

    with t3:
        st.header('Analysis')
        df3 = st.session_state['data'].sort_values('Date')
        if df3.empty:
            st.info('No data')
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

            # Plot
            series = st.multiselect('Series', ACCOUNT_FIELDS, ACCOUNT_FIELDS)
            if series:
                fig = go.Figure()
                for f in series:
                    fig.add_trace(go.Scatter(x=sel.index, y=sel[f] / 1e6, mode='lines+markers', name=f))
                fig.update_layout(xaxis_title='Month-Year', yaxis_title='Amount (Million)')
                fig.update_yaxes(tickformat=',.0f', autorange=True)
                st.plotly_chart(fig, use_container_width=True)

            # Vertical table
            st.subheader('Data Table')
            table = sel[series].T
            table.columns = sel.index
            table_display = table.applymap(fmt)
            st.dataframe(table_display, use_container_width=True)

if __name__ == '__main__':
    main()
