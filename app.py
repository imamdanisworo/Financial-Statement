import streamlit as st
import pandas as pd
import datetime
import calendar
import os
import plotly.graph_objects as go

# Sticky tabs
st.markdown(
    '''<style>div[role="tablist"]{position:sticky;top:0;background:#fff;z-index:999}</style>''', unsafe_allow_html=True)

# Fields
ACCOUNT_FIELDS=[
    'Current Asset','Non Current Asset','Total Asset',
    'Current Liabilities','Non Current Liabilities','Total Liabilities',
    'Equity','Revenue','Administration Exp','Employee Expense',
    'Marketing Expense','Rent Expense','Right of Use Assets Expense',
    'Depreciation Expense','Total Operating Exp.','Operating Income',
    'Other Income and Expense','Net Income','Tax','Income After Tax'
]
# Data file
DATA_DIR='data';CSV=os.path.join(DATA_DIR,'financial_data.csv')
os.makedirs(DATA_DIR,exist_ok=True)
# Load
def load_data():
    if os.path.exists(CSV):df=pd.read_csv(CSV)
    else:df=pd.DataFrame(columns=['Date']+ACCOUNT_FIELDS)
    for c in ['Date']+ACCOUNT_FIELDS:
        if c not in df:df[c]=0
    df['Date']=pd.to_datetime(df['Date'],errors='coerce')
    for f in ACCOUNT_FIELDS:df[f]=pd.to_numeric(df[f],errors='coerce').fillna(0)
    return df
# Save

def save_row(df,date,vals):
    ts=pd.Timestamp(date)
    if (df['Date']==ts).any():df.loc[df['Date']==ts,ACCOUNT_FIELDS]=vals
    else: r={'Date':ts};r.update(dict(zip(ACCOUNT_FIELDS,vals)));df=pd.concat([df,pd.DataFrame([r])],ignore_index=True)
    df.to_csv(CSV,index=False);return df
# Delete
def delete_date(df,date_str):
    ts=pd.Timestamp(date_str);df=df[df['Date']!=ts].reset_index(drop=True);df.to_csv(CSV,index=False);return df
# fmt
def fmt(x):
    if pd.isna(x):return''
    return f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}"
# main

def main():
    df=load_data();st.session_state['data']=df
    t1,t2,t3=st.tabs(['Input','Storage','Analysis'])
    with t1:
        st.header('Input')
        with st.form('f',clear_on_submit=True):
            years=list(range(2000,datetime.date.today().year+2))
            yr=st.selectbox('Year',years,index=len(years)-1)
            mos=list(calendar.month_name)[1:]
            mo=st.selectbox('Month',mos,index=datetime.date.today().month-1)
            vals=[st.number_input(f,0.0,format='%.2f') for f in ACCOUNT_FIELDS]
            if st.form_submit_button('Add'):
                d=datetime.date(yr,mos.index(mo)+1,calendar.monthrange(yr,mos.index(mo)+1)[1])
                df=save_row(st.session_state['data'],d,vals)
                st.session_state['data']=df;st.success('Saved')
    with t2:
        st.header('Storage');df2=st.session_state['data'].sort_values('Date')
        if df2.empty:st.info('No data')
        else:
            df2['DS']=df2['Date'].dt.strftime('%Y-%m-%d')
            piv=df2.set_index('DS')[ACCOUNT_FIELDS].T.applymap(fmt)
            st.dataframe(piv,use_container_width=True)
            for d in piv.columns:
                if st.button(f'Del {d}'):df2=delete_date(st.session_state['data'],d);st.session_state['data']=df2;st.success('Del')
    with t3:
        st.header('Analysis');df3=st.session_state['data'].sort_values('Date')
        if df3.empty:st.info('No data')
        else:
            yrs=sorted(df3['Date'].dt.year.unique());ms=list(calendar.month_name)[1:]
            c1,c2=st.columns(2)
            with c1: y1=st.selectbox('From Year',yrs,0);m1=st.selectbox('From Month',ms,0)
            with c2: y2=st.selectbox('To Year',yrs,len(yrs)-1);m2=st.selectbox('To Month',ms,len(ms)-1)
            sd=pd.Timestamp(datetime.date(y1,ms.index(m1)+1,1))
            ed=pd.Timestamp(datetime.date(y2,ms.index(m2)+1,calendar.monthrange(y2,ms.index(m2)+1)[1]))
            mask=(df3['Date']>=sd)&(df3['Date']<=ed)
            sel=df3.loc[mask].copy();sel['MY']=sel['Date'].dt.strftime('%b %Y');sel.set_index('MY',inplace=True)
            s=st.multiselect('Series',ACCOUNT_FIELDS,ACCOUNT_FIELDS)
            if s:
                fig=go.Figure();
                for f in s:fig.add_trace(go.Scatter(x=sel.index,y=sel[f]/1e6,mode='lines+markers',name=f))
                fig.update_layout(xaxis_title='Month-Year',yaxis_title='Amount M')
                fig.update_yaxes(tickformat=',.0f',autorange=True)
                st.plotly_chart(fig,use_container_width=True)
                rd=sel[s].applymap(fmt).reset_index();rd.index+=1;st.dataframe(rd,use_container_width=True)

if __name__=='__main__':main()
