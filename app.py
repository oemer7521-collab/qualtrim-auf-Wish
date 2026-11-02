import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Financial Analytics Terminal", layout="wide", initial_sidebar_state="collapsed")

# 1. Custom CSS für Card-Grid-Design
st.markdown("""
<style>
    .stApp {
        background-color: #f3f4f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 95%;
    }
    .metric-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
        padding: 0 4px;
    }
    .metric-card-title {
        font-size: 13.5px;
        font-weight: 600;
        color: #374151;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .kpi-pill {
        background-color: #fca5a5;
        color: #991b1b;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        letter-spacing: 0.5px;
    }
    .price-change-badge {
        background-color: #dcfce7;
        color: #15803d;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
    }
    div[data-testid="stDataFrame"] {
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        padding: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Ticker Auflösung
def resolve_ticker(query: str) -> str:
    query = query.strip()
    if not query:
        return ""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        quotes = res.get("quotes", [])
        if quotes:
            return quotes[0].get("symbol", query.upper())
    except Exception:
        pass
    return query.upper()

col_search, col_spacer = st.columns([2, 3])
with col_search:
    user_query = st.text_input("Unternehmen oder Ticker eingeben:", value="Apple", label_visibility="collapsed")
    ticker_symbol = resolve_ticker(user_query)

if not ticker_symbol:
    st.stop()

ticker = yf.Ticker(ticker_symbol)

with st.spinner(f"Lade Finanzdaten für {ticker_symbol}..."):
    try:
        info = ticker.info or {}
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        dividends = ticker.dividends
        hist = ticker.history(period="1y")
    except Exception as e:
        st.error(f"Fehler beim Datenabruf: {e}")
        st.stop()

if not info or financials.empty:
    st.warning(f"Keine ausreichenden Daten für '{user_query}' ({ticker_symbol}) gefunden.")
    st.stop()

# Plotly Base Styling Funktion
def build_clean_chart(fig, y_prefix="", y_suffix=""):
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=45, r=15, t=15, b=45),
        height=210,
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="#e5e7eb",
            tickangle=-45,
            tickfont=dict(size=10, color="#6b7280")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f3f4f6",
            gridwidth=1,
            showline=False,
            tickfont=dict(size=10, color="#6b7280"),
            tickprefix=y_prefix,
            ticksuffix=y_suffix
        )
    )
    return fig

years = sorted(financials.columns)
date_labels = [pd.to_datetime(y).strftime("%Y") for y in years]

def get_row(key, df):
    return df.loc[key] if key in df.index else pd.Series(0, index=df.columns)

rev = get_row("Total Revenue", financials)
ebitda = get_row("EBITDA", financials)
net_inc = get_row("Net Income", financials)
ocf = get_row("Operating Cash Flow", cashflow)
capex = get_row("Capital Expenditure", cashflow)
fcf = ocf.fillna(0) + capex.fillna(0)

# Kursveränderung (1Y)
curr_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
price_change_pct = 0.0
if not hist.empty and len(hist) > 1:
    first_price = hist['Close'].iloc[0]
    last_price = hist['Close'].iloc[-1]
    price_change_pct = ((last_price - first_price) / first_price) * 100

st.markdown(f"## {info.get('longName', ticker_symbol)} ({ticker_symbol})")

# REIHE 1: VISUELLES KARTEN-RASTER
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div
