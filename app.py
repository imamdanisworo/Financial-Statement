import streamlit as st
import pandas as pd
import datetime
import calendar
import os
import plotly.graph_objects as go

# --- Floating navigation buttons (scrollable to anchors) ---
st.markdown(
    '''<style>
    .floating-tabs {
        position: fixed;
        top: 50%;
        right: 0;
        transform: translateY(-50%);
        z-index: 1000;
        background-color: white;
        border: 1px solid #ddd;
        border-right: none;
        box-shadow: -2px 2px 5px rgba(0,0,0,0.1);
    }
    .floating-tabs button {
        display: block;
        width: 100%;
        border: none;
        background: white;
        padding: 10px 15px;
        text-align: left;
        font-size: 14px;
        cursor: pointer;
        border-bottom: 1px solid #eee;
    }
    .floating-tabs button:hover {
        background-color: #f5f5f5;
    }
    </style>
    <div class="floating-tabs">
        <form action="#input" method="get"><button type="submit">📅 Input</button></form>
        <form action="#storage" method="get"><button type="submit">📂 Storage</button></form>
        <form action="#analysis" method="get"><button type="submit">📊 Analysis</button></form>
    </div>
    ''', unsafe_allow_html=True)

# Anchors for navigation
st.markdown('<a name="input"></a>', unsafe_allow_html=True)

# Paths and fields
years = list(range(2000, datetime.date.today().year + 2))
ACCOUNT_FIELDS = [...]
RATIO_FIELDS = {...}  # same as before
csv_file = os.path.join('data', 'financial_data.csv')
os.makedirs('data', exist_ok=True)

fmt = lambda x: '' if pd.isna(x) else f"Rp. {int(x):,}" if float(x).is_integer() else f"Rp. {x:,.2f}"
fmt_decimal = lambda x: '' if pd.isna(x) else f"{x:.2f}"
fmt_percent = lambda x: '' if pd.isna(x) else f"{x*100:.2f}%"

def load_data():
    if os.path.exists(csv_file): df = pd.read_csv(csv_file)
    else: df = pd.DataFrame(columns=['Date'] + ACCOUNT_FIELDS)
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

# Main UI
st.title("📊 Financial Dashboard")
df = load_data()
st.session_state['data'] = df

# Tab 1
st.markdown('<a name="input"></a>', unsafe_allow_html=True)
st.header('📅 Input Financial Data')
with st.form('f1', clear_on_submit=True):
    today = datetime.date.today()
    yr = st.selectbox('Year', years, index=years.index(today.year))
    mos = list(calendar.month_name)[1:]
    mo = st.selectbox('Month', mos, index=today.month - 1)
    vals = [st.number_input(f, value=0.0, format="%.2f") for f in ACCOUNT_FIELDS]
    if st.form_submit_button('Save Data'):
        day = calendar.monthrange(yr, mos.index(mo) + 1)[1]
        date = datetime.date(yr, mos.index(mo) + 1, day)
        df = save_row(st.session_state['data'], date, vals)
        st.session_state['data'] = df

# Tab 2
st.markdown('<a name="storage"></a>', unsafe_allow_html=True)
st.header('📂 Stored Financial Data (in Millions)')
df2 = st.session_state['data'].sort_values('Date')
if df2.empty:
    st.info('No data available.')
else:
    df2['DS'] = df2['Date'].dt.strftime('%b %Y')
    piv = df2.set_index('DS')[ACCOUNT_FIELDS].T.astype(float) / 1e6
    piv_display = piv.applymap(fmt)
    st.dataframe(piv_display, use_container_width=True)
    for d in piv.columns:
        if st.button(f'Delete {d}', key=f'del_{d}'):
            df2 = delete_date(st.session_state['data'], d)
            st.session_state['data'] = df2
            st.success(f"Deleted entry for {d}.")

# Tab 3
st.markdown('<a name="analysis"></a>', unsafe_allow_html=True)
st.header('📊 Financial Analysis')
df3 = st.session_state['data'].sort_values('Date')
if df3.empty:
    st.info('No data to analyze.')
else:
    yrs = sorted(df3['Date'].dt.year.unique())
    mos = list(calendar.month_name)[1:]
    c1, c2 = st.columns(2)
    with c1:
        y1 = st.selectbox('From Year', yrs)
        m1 = st.selectbox('From Month', mos)
    with c2:
        y2 = st.selectbox('To Year', yrs, index=len(yrs)-1)
        m2 = st.selectbox('To Month', mos, index=len(mos)-1)
    sd = pd.Timestamp(datetime.date(y1, mos.index(m1)+1, 1))
    ed = pd.Timestamp(datetime.date(y2, mos.index(m2)+1, calendar.monthrange(y2, mos.index(m2)+1)[1]))
    sel = df3[(df3['Date']>=sd)&(df3['Date']<=ed)].copy()
    sel['MY'] = sel['Date'].dt.strftime('%b %Y')
    sel.set_index('MY', inplace=True)

    series = st.multiselect('Select Series to Plot', ACCOUNT_FIELDS, ACCOUNT_FIELDS)
    if series:
        fig = go.Figure()
        for f in series:
            fig.add_trace(go.Scatter(x=sel.index, y=sel[f] / 1e6, mode='lines+markers', name=f))
        fig.update_layout(
            title='Financial Trend',
            xaxis_title='Month-Year',
            yaxis_title='Amount (in Millions)',
            legend=dict(orientation='h', x=0.5, xanchor='center', y=-0.3),
            margin=dict(t=50, b=100)
        )
        st.plotly_chart(fig, use_container_width=True)
        table = (sel[series].T / 1e6).applymap(fmt)
        st.dataframe(table, use_container_width=True)

    st.subheader("📈 Financial Ratios")
    ratio_df = pd.DataFrame(index=sel.index)
    for name, (func, _) in RATIO_FIELDS.items():
        ratio_df[name] = func(sel)
    ratio_table = ratio_df.T
    for name, (_, ftype) in RATIO_FIELDS.items():
        ratio_table.loc[name] = ratio_table.loc[name].map(fmt_percent if ftype == 'percent' else fmt_decimal)
    st.dataframe(ratio_table, use_container_width=True)

# Run
if __name__ == '__main__':
    pass
