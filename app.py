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
os.makedirs(data_dir, exist_ok=True)

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

# Save/update row
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

# Delete row
def delete_date(df, date_str):
    ts = pd.Timestamp(date_str)
    df = df[df['Date'] != ts].reset_index(drop=True)
    df.to_csv(csv_file, index=False)
    return df

# Format
def fmt(x):
    if pd.isna(x): return ''
    return f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}"

# App
def main():
    df = load_data()
    st.session_state['data'] = df
    t1, t2, t3 = st.tabs(['Input','Storage','Analysis'])

    with t1:
        st.header('Input Data')
        with st.form('f1', clear_on_submit=True):
            year = st.selectbox('Year', list(range(2000, datetime.date.today().year+2)), index=-1)
            month = st.selectbox('Month', list(calendar.month_name)[1:], index=datetime.date.today().month-1)
            vals = [st.number_input(f,0.0,format='%.2f') for f in ACCOUNT_FIELDS]
            if st.form_submit_button('Add'):
                dy = calendar.monthrange(year, list(calendar.month_name).index(month))[1]
                d = datetime.date(year, list(calendar.month_name).index(month), dy)
                df = save_row(st.session_state['data'], d, vals)
                st.session_state['data'] = df
                st.success(f'Saved for {month} {year}')

    with t2:
        st.header('Storage')
        df2 = st.session_state['data'].sort_values('Date')
        if df2.empty: st.info('No data'); return
        df2['DS'] = df2['Date'].dt.strftime('%Y-%m-%d')
        piv = df2.set_index('DS')[ACCOUNT_FIELDS].T.applymap(fmt)
        st.dataframe(piv,use_container_width=True)
        for i,ds in enumerate(piv.columns):
            if st.button('Del '+ds, key=i):
                df = delete_date(st.session_state['data'], ds)
                st.session_state['data']=df
                st.success(f'Deleted {ds}')

    with t3:
        st.header('Analysis')
        df3 = st.session_state['data'].sort_values('Date')
        if df3.empty: st.info('No data'); return
        yrs = sorted(df3['Date'].dt.year.unique())
        mos = list(calendar.month_name)[1:]
        c1,c2 = st.columns(2)
        with c1:
            y1=st.selectbox('From Year',yrs,0)
            m1=st.selectbox('From Month',mos,0)
        with c2:
            y2=st.selectbox('To Year',yrs,len(yrs)-1)
            m2=st.selectbox('To Month',mos,len(mos)-1)
        sd = datetime.date(y1,mos.index(m1)+1,1)
        ed_day = calendar.monthrange(y2,mos.index(m2)+1)[1]
        ed = datetime.date(y2,mos.index(m2)+1,ed_day)
        sel = df3[(df3['Date']>=sd)&(df3['Date']<=ed)].copy()
        sel['MY']=sel['Date'].dt.strftime('%b %Y')
        sel.set_index('MY',inplace=True)
        series = st.multiselect('Series',ACCOUNT_FIELDS,ACCOUNT_FIELDS)
        if series:
            fig=go.Figure()
            for s in series:
                fig.add_trace(go.Scatter(x=sel.index,y=sel[s]/1e6,mode='lines+markers',name=s,
                                          hovertemplate=f"{s}: %{{y:,.0f}} Mio<br>%{{x}}"))
            fig.update_layout(xaxis_title='Month-Year',yaxis_title='Amount(M)')
            fig.update_yaxes(tickformat=',.0f',autorange=True)
            st.plotly_chart(fig,use_container_width=True)
            rt=sel[series].applymap(fmt).reset_index();rt.index+=1;st.dataframe(rt,use_container_width=True)

if __name__=='__main__':main()
