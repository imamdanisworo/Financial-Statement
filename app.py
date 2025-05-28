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

# Account fields: Correct order with Depreciation Expense below ROU
ACCOUNT_FIELDS = [
    'Current Asset', 'Non Current Asset', 'Total Asset',
    'Current Liabilities', 'Non Current Liabilities', 'Total Liabilities',
    'Equity', 'Revenue', 'Administration Exp', 'Employee Expense',
    'Marketing Expense', 'Rent Expense', 'Right of Use Assets Expense',
    'Depreciation Expense', 'Total Operating Exp.', 'Operating Income',
    'Other Income and Expense', 'Net Income', 'Tax', 'Income After Tax'
]

data_dir = 'data'
csv_file = os.path.join(data_dir, 'financial_data.csv')

os.makedirs(data_dir, exist_ok=True)

# Load or create data
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

# Save/update a row
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

# Delete by date string
def delete_date(df, date_str):
    ts = pd.Timestamp(date_str)
    df = df[df['Date'] != ts].reset_index(drop=True)
    df.to_csv(csv_file, index=False)
    return df

# Format helper
def fmt(x):
    if pd.isna(x): return ''
    return f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}"

# Main

def main():
    df = load_data()
    st.session_state['data'] = df
    tab1, tab2, tab3 = st.tabs(['Input','Storage','Analysis'])

    # Input tab
    with tab1:
        st.header('Input Monthly Financial Data')
        with st.form('input_form', clear_on_submit=True):
            years = list(range(2000, datetime.date.today().year+2))
            year = st.selectbox('Year', years, index=len(years)-1)
            months = list(calendar.month_name)[1:]
            month = st.selectbox('Month', months, index=datetime.date.today().month-1)
            vals = [st.number_input(field, value=0.0, format='%.2f') for field in ACCOUNT_FIELDS]
            if st.form_submit_button('Add'):
                day = calendar.monthrange(year, months.index(month)+1)[1]
                date = datetime.date(year, months.index(month)+1, day)
                df = save_row(st.session_state['data'], date, vals)
                st.session_state['data'] = df
                st.success(f'Saved data for {month} {year}')

    # Storage tab
    with tab2:
        st.header('Stored Data')
        df2 = st.session_state['data'].sort_values('Date')
        if df2.empty:
            st.info('No data to display')
        else:
            df2['DS'] = df2['Date'].dt.strftime('%Y-%m-%d')
            piv = df2.set_index('DS')[ACCOUNT_FIELDS].T.applymap(fmt)
            st.dataframe(piv, use_container_width=True)
            for d in piv.columns:
                if st.button(f'Delete {d}'):
                    df2 = delete_date(st.session_state['data'], d)
                    st.session_state['data'] = df2
                    st.success(f'Deleted data for {d}')

    # Analysis tab
    with tab3:
        st.header('Data Analysis')
        df3 = st.session_state['data'].sort_values('Date')
        if df3.empty:
            st.info('No data to analyze')
        else:
            years_unique = sorted(df3['Date'].dt.year.unique())
            months = list(calendar.month_name)[1:]
            c1, c2 = st.columns(2)
            with c1:
                y1 = st.selectbox('From Year', years_unique, index=0)
                m1 = st.selectbox('From Month', months, index=0)
            with c2:
                y2 = st.selectbox('To Year', years_unique, index=len(years_unique)-1)
                m2 = st.selectbox('To Month', months, index=len(months)-1)
            sd = datetime.date(y1, months.index(m1)+1, 1)
            ed = datetime.date(y2, months.index(m2)+1, calendar.monthrange(y2, months.index(m2)+1)[1])
            sel = df3[(df3['Date']>=sd)&(df3['Date']<=ed)].copy()
            sel['MY'] = sel['Date'].dt.strftime('%b %Y')
            sel.set_index('MY', inplace=True)

            # Plot
            series = st.multiselect('Select Metrics', ACCOUNT_FIELDS, default=ACCOUNT_FIELDS)
            if series:
                fig = go.Figure()
                for metric in series:
                    fig.add_trace(go.Scatter(
                        x=sel.index, y=sel[metric]/1e6,
                        mode='lines+markers', name=metric,
                        hovertemplate=f"{metric}: %{{y:,.0f}} Mio<br>%{{x}}"
                    ))
                fig.update_layout(xaxis_title='Month-Year', yaxis_title='Amount (Million)')
                fig.update_yaxes(tickformat=',.0f', autorange=True)
                st.plotly_chart(fig, use_container_width=True)
                raw_df = sel[series].applymap(fmt).reset_index()
                raw_df.index += 1
                st.subheader('Raw Data Table')
                st.dataframe(raw_df, use_container_width=True)

if __name__=='__main__':
    main()
