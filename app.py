import streamlit as st
import pandas as pd
import datetime
import calendar
import os
import plotly.graph_objects as go

# --- Sticky tab bar floated to right CSS ---
st.markdown(
    '''<style>
    .main > div {
        display: flex;
        flex-direction: row-reverse;
    }
    div[role="tablist"] {
        position: sticky;
        top: 0;
        z-index: 1000;
        background-color: white;
        width: 200px;
        align-self: flex-start;
        margin-left: auto;
        border-left: 1px solid #eee;
        padding-left: 1rem;
    }
    </style>''', unsafe_allow_html=True)

# (rest of the code remains unchanged)
