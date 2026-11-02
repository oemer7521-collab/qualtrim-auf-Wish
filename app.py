import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Financial Analytics Terminal", layout="wide", initial_sidebar_state="collapsed")

# 1. Custom CSS für Terminal-Layout und saubere Buttons in den Kacheln
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 96% !important;
    }
    
    .search-nav-container {
        background: #ffffff;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        padding: 14px 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        margin-bottom: 16px;
    }
    
    .company-banner {
        background: #ffffff;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        padding: 18px 24px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .company-name-text {
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.5px;
    }
    .company-sub-text {
        font-size: 13px;
        color: #64748b;
        margin-top: 2px;
    }

    .metric-card-box {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 10px 14px 4px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        margin-bottom: 12px;
    }
    .metric-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #1e293b;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .kpi-badge {
        background-color: #fee2e2;
        color: #b91c1c;
        font-size: 9.5px;
        font-weight: 700;
        padding: 1px 5px;
        border-radius: 4px;
    }
    .price-badge-up {
        background-color: #dcfce7;
        color: #15803d;
        font-size: 11px;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 4px;
    }
    .price-badge-down {
        background-color: #fee2e2;
        color: #b91c1c;
        font-size: 11px;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 4px;
    }

    .section-label {
        font-size: 14px;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin: 18px 0 8px 4px;
    }

    /* Modal / Pop-up Breite */
    div[data-testid="stDialog"] div[role="dialog"] {
        width: 80vw !important;
        max-width: 1100px !important;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #f8fafc !important;
        font-size: 14px !important;
        color: #0f172a !important;
    }
    div[data-testid="stDataFrame"] {
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        padding: 6px;
    }
</style>
""", unsafe_allow_html=True)

# 2. State-Management & Ticker-Auflösung
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "ServiceNow"

def set_ticker(ticker_name):
    st.session_state.selected_ticker = ticker_name

def resolve_ticker(query: str) -> str:
    query = query.strip()
    if not query:
        return "NOW"
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

# 3. Interaktive Such- und Navigationsleiste
st.markdown('<div class="search-nav-container">', unsafe_allow_html=True)
col_nav1, col_nav2, col_nav3 = st.columns([3.5, 1.3, 0.8])

with col_nav1:
    search_input = st.text_input(
        "Suche",
        value=st.session_state.selected_ticker,
        placeholder="🔍 Suche nach Unternehmen oder Symbol (z.B. Microsoft, NOW, NVDA, SAP, Apple)...",
        label_visibility="collapsed"
    )

with col_nav2:
    period_type = st.radio("Intervall", ["Jährlich", "Quartal"], horizontal=True, label_visibility="collapsed")

with col_nav3:
    st.button("Laden", use_container_width=True)

st.caption("Schnellauswahl:")
chip_cols = st.columns(8)
quick_picks = [("ServiceNow", "NOW"), ("Apple", "AAPL"), ("Microsoft", "MSFT"), ("Nvidia", "NVDA"), ("Amazon", "AMZN"), ("Alphabet", "GOOGL"), ("Tesla", "TSLA"), ("SAP", "SAP")]
for i, (name, sym) in enumerate(quick_picks):
    with chip_cols[i]:
        if st.button(f"{sym}", key=f"chip_{sym}", use_container_width=True):
            set_ticker(sym)
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

symbol = resolve_ticker(search_input)
ticker = yf.Ticker(symbol)

with st.spinner(f"Lade Finanzdaten für {symbol}..."):
    try:
        info = ticker.info or {}
        is_quarterly = (period_type == "Quartal")
        financials = ticker.quarterly_financials if is_quarterly else ticker.financials
        balance_sheet = ticker.quarterly_balance_sheet if is_quarterly else ticker.balance_sheet
        cashflow = ticker.quarterly_cashflow if is_quarterly else ticker.cashflow
        dividends = ticker.dividends
        hist = ticker.history(period="1y")
    except Exception as e:
        st.error(f"Fehler beim Datenabruf: {e}")
        st.stop()

if not info or financials.empty:
    st.warning(f"Keine Kennzahlen für '{search_input}' ({symbol}) gefunden.")
    st.stop()

company_name = info.get("longName", symbol)
sector = info.get("sector", "N/A")
industry = info.get("industry", "N/A")
currency = info.get("currency", "USD")
curr_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
m_cap = info.get("marketCap", 0)

st.markdown(f"""
<div class="company-banner">
    <div>
        <div class="company-name-text">{company_name} ({symbol})</div>
        <div class="company-sub-text">{sector} • {industry} • Währung in {currency}</div>
    </div>
    <div style="text-align: right;">
        <div style="font-size: 24px; font-weight: 700; color: #0f172a;">{curr_price:,.2f} {currency}</div>
        <div style="font-size: 13px; color: #64748b; font-weight: 500;">Market Cap: {m_cap/1e9:,.1f}B {currency}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. Plotly Helper-Funktionen
def clean_chart(fig, y_prefix="", y_suffix="", show_legend=False):
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=42, r=10, t=10, b=35),
        height=190,
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9.5)),
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="#e2e8f0",
            tickangle=-35,
            tickfont=dict(size=9.5, color="#64748b")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            gridwidth=1,
            showline=False,
            tickfont=dict(size=9.5, color="#64748b"),
            tickprefix=y_prefix,
            ticksuffix=y_suffix
        )
    )
    return fig

# Spalten vorbereiten
cols_chrono = sorted(financials.columns)
date_labels = [
    pd.to_datetime(d).strftime("Q%q '%y") if is_quarterly else pd.to_datetime(d).strftime("%Y") 
    for d in cols_chrono
]

def get_row(key, df):
    if key in df.index:
        return df.loc[key]
    for idx in df.index:
        if key.lower() in str(idx).lower():
            return df.loc[idx]
    return pd.Series(0, index=df.columns)

rev = get_row("Total Revenue", financials)
gp = get_row("Gross Profit", financials)
ebit = get_row("Operating Income", financials)
ebitda = get_row("EBITDA", financials)
net_inc = get_row("Net Income", financials)
ocf = get_row("Operating Cash Flow", cashflow)
capex = get_row("Capital Expenditure", cashflow)
fcf = ocf.fillna(0) + capex.fillna(0)
shares = info.get("sharesOutstanding", 1) or 1

total_assets = get_row("Total Assets", balance_sheet)
total_liab = get_row("Total Liabilities Net Minority Interest", balance_sheet)
cash = get_row("Cash And Cash Equivalents", balance_sheet)
st_debt = get_row("Current Debt", balance_sheet)
lt_debt = get_row("Long Term Debt", balance_sheet)
total_debt = st_debt.fillna(0) + lt_debt.fillna(0)
net_debt = total_debt - cash.fillna(0)
equity = get_row("Stockholders Equity", balance_sheet)

price_chg = 0.0
if not hist.empty and len(hist) > 1:
    price_chg = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100

def calc_margin_series(numerator_series):
    vals = []
    for y in cols_chrono:
        r = rev.get(y, 0)
        num = numerator_series.get(y, 0)
        vals.append((num / r * 100) if (pd.notnull(r) and r != 0) else 0)
    return vals

# 5. VOLLBILD-MODAL (Pop-up mit Detailanalyse)
@st.dialog("Detaillierte Metrik-Analyse")
def open_detail_modal(metric_name, series_data, is_pct=False, unit_suffix="B", color="#3b82f6", chart_type="bar", description=""):
    st.subheader(f"{metric_name} — Deep Dive")
    st.caption(f"Historische Zeitreihe ({period_type}) für {company_name}")
    
    # Großes Plotly-Chart
    fig = go.Figure()
    if chart_type == "bar":
        fig.add_trace(go.Bar(
            x=date_labels, 
            y=series_data, 
            marker_color=color, 
            text=[f"{v:.2f}{'%' if is_pct else unit_suffix}" for v in series_data],
            textposition='auto'
        ))
    elif chart_type == "scatter":
        fig.add_trace(go.Scatter(
            x=date_labels, 
            y=series_data, 
            mode='lines+markers', 
            line=dict(color=color, width=3), 
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        template="plotly_white",
        height=380,
        margin=dict(l=50, r=20, t=20, b=40),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", ticksuffix="%" if is_pct else unit_suffix)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Historische Datentabelle & Wachstumsraten
    df_detail = pd.DataFrame({
        "Periode": date_labels,
        "Wert": [f"{v:.2f} %" if is_pct else f"{v:,.2f} {unit_suffix}" for v in series_data]
    })
    
    # Wachstumsrate (YoY bzw. QoQ)
    growth_rates = ["-"]
    for i in range(1, len(series_data)):
        prev = series_data[i-1]
        curr = series_data[i]
        if prev != 0 and pd.notnull(prev):
            pct = ((curr - prev) / abs(prev)) * 100
            growth_rates.append(f"{pct:+.2f}%")
        else:
            growth_rates.append("N/A")
    df_detail["Wachstum"] = growth_rates
    
    col_d1, col_d2 = st.columns([1.5, 1])
    with col_d1:
        st.write("**Historische Zahlen & Wachstumsraten**")
        st.dataframe(df_detail.T, use_container_width=True)
    with col_d2:
        st.write("**Börsen-Kontext & Analyse**")
        st.info(description if description else f"Diese Kennzahl spiegelt die fundamentale Entwicklung im Bereich {metric_name} wider.")

# ==============================================================================
# REIHE 1: Price, Revenue, Gross Profit, Operating Income
# ==============================================================================
st.markdown('<div class="section-label">Ertrag & Performance</div>', unsafe_allow_html=True)
r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)

with r1_c1:
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        badge_cls = "price-badge-up" if price_chg >= 0 else "price-badge-down"
        arrow = "↑" if price_chg >= 0 else "↓"
        st.markdown(f'<span class="metric-card-title">Price <span class="{badge_cls}">{arrow} {price_chg:+.2f}%</span></span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_p", help="Vollbild / Details"):
            open_detail_modal("Aktienkurs (1Y)", hist['Close'].tolist(), is_pct=False, unit_suffix="", color="#16a34a", chart_type="scatter", description="1-Jahres-Kursverlauf des Wertpapiers.")
    if not hist.empty:
        fig_p = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', line=dict(color="#16a34a", width=1.8), fill='tozeroy', fillcolor='rgba(22, 163, 74, 0.1)'))
        st.plotly_chart(clean_chart(fig_p, y_prefix="$"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r1_c2:
    rev_vals = [rev.get(y, 0) / 1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Revenue</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_r", help="Vollbild / Details"):
            open_detail_modal("Revenue (Umsatz)", rev_vals, is_pct=False, unit_suffix="B", color="#ea580c", chart_type="bar", description="Gesamtumsatz über die gewählten Berichtszeiträume in Milliarden USD.")
    fig_r = go.Figure(go.Bar(x=date_labels, y=rev_vals, marker_color="#ea580c", width=0.45))
    st.plotly_chart(clean_chart(fig_r, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r1_c3:
    gp_vals = [gp.get(y, 0) / 1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title"><span class="kpi-badge">KPI</span> Gross Profit</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_gp", help="Vollbild / Details"):
            open_detail_modal("Gross Profit (Bruttogewinn)", gp_vals, is_pct=False, unit_suffix="B", color="#d97706", chart_type="bar", description="Bruttogewinn nach Abzug der direkten Herstellungskosten (COGS).")
    fig_g = go.Figure(go.Bar(x=date_labels, y=gp_vals, marker_color="#d97706", width=0.45))
    st.plotly_chart(clean_chart(fig_g, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r1_c4:
    ebit_vals = [ebit.get(y, 0) / 1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title"><span class="kpi-badge">KPI</span> Operating Income</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_ebit", help="Vollbild / Details"):
            open_detail_modal("Operating Income (EBIT)", ebit_vals, is_pct=False, unit_suffix="B", color="#64748b", chart_type="bar", description="Operativer Gewinn vor Zinsen und Steuern.")
    fig_eb = go.Figure(go.Bar(x=date_labels, y=ebit_vals, marker_color="#64748b", width=0.45))
    st.plotly_chart(clean_chart(fig_eb, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# REIHE 2: EBITDA, Net Income, Free Cash Flow, EPS
# ==============================================================================
r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)

with r2_c1:
    ebitda_vals = [ebitda.get(y, 0) / 1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">EBITDA</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_ebitda", help="Vollbild / Details"):
            open_detail_modal("EBITDA", ebitda_vals, is_pct=False, unit_suffix="B", color="#93c5fd", chart_type="bar", description="Gewinn vor Zinsen, Steuern, Abschreibungen auf Sachanlagen und immaterielle Vermögensgegenstände.")
    fig_ebitda = go.Figure(go.Bar(x=date_labels, y=ebitda_vals, marker_color="#93c5fd", width=0.45))
    st.plotly_chart(clean_chart(fig_ebitda, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r2_c2:
    ni_vals = [net_inc.get(y, 0) / 1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Net Income</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_ni", help="Vollbild / Details"):
            open_detail_modal("Net Income (Nettogewinn)", ni_vals, is_pct=False, unit_suffix="B", color="#fca5a5", chart_type="bar", description="Reingewinn nach Steuern und Zinsaufwendungen.")
    fig_ni = go.Figure(go.Bar(x=date_labels, y=ni_vals, marker_color="#fca5a5", width=0.45))
    st.plotly_chart(clean_chart(fig_ni, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r2_c3:
    fcf_vals = [fcf.get(y, 0) / 1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Free Cash Flow</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_fcf", help="Vollbild / Details"):
            open_detail_modal("Free Cash Flow (FCF)", fcf_vals, is_pct=False, unit_suffix="B", color="#b45309", chart_type="bar", description="Operativer Cashflow minus Sachinvestitionen (CapEx) – der tatsächlich frei verfügbare Cashflow.")
    fig_f = go.Figure(go.Bar(x=date_labels, y=fcf_vals, marker_color="#b45309", width=0.45))
    st.plotly_chart(clean_chart(fig_f, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r2_c4:
    eps_vals = [net_inc.get(y, 0) / shares for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">EPS</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_eps", help="Vollbild / Details"):
            open_detail_modal("Earnings Per Share (EPS)", eps_vals, is_pct=False, unit_suffix="", color="#facc15", chart_type="bar", description="Gewinn je Aktie auf Basis ausstehender Aktien.")
    fig_e = go.Figure(go.Bar(x=date_labels, y=eps_vals, marker_color="#facc15", width=0.45))
    st.plotly_chart(clean_chart(fig_e, y_prefix="$"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# REIHE 3: MARGENPROFIL
# ==============================================================================
st.markdown('<div class="section-label">Margenprofil & Profitabilität (%)</div>', unsafe_allow_html=True)
r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)

with r3_c1:
    gm_vals = calc_margin_series(gp)
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Gross Margin</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_gm", help="Vollbild / Details"):
            open_detail_modal("Gross Margin (%)", gm_vals, is_pct=True, color="#d97706", chart_type="scatter", description="Bruttomarge: Verhältnis von Bruttogewinn zu Gesamtumsatz.")
    fig_gm = go.Figure(go.Scatter(x=date_labels, y=gm_vals, mode='lines+markers', line=dict(color="#d97706", width=2.2), marker=dict(size=5)))
    st.plotly_chart(clean_chart(fig_gm, y_suffix="%"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r3_c2:
    om_vals = calc_margin_series(ebit)
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Operating Margin</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_om", help="Vollbild / Details"):
            open_detail_modal("Operating Margin (%)", om_vals, is_pct=True, color="#64748b", chart_type="scatter", description="Operative Marge (EBIT-Marge): Misst die Effizienz des Kerngeschäfts.")
    fig_om = go.Figure(go.Scatter(x=date_labels, y=om_vals, mode='lines+markers', line=dict(color="#64748b", width=2.2), marker=dict(size=5)))
    st.plotly_chart(clean_chart(fig_om, y_suffix="%"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r3_c3:
    em_vals = calc_margin_series(ebitda)
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">EBITDA Margin</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_em", help="Vollbild / Details"):
            open_detail_modal("EBITDA Margin (%)", em_vals, is_pct=True, color="#3b82f6", chart_type="scatter", description="EBITDA-Marge: Operative Rentabilität bereinigt um Abschreibungen.")
    fig_em = go.Figure(go.Scatter(x=date_labels, y=em_vals, mode='lines+markers', line=dict(color="#3b82f6", width=2.2), marker=dict(size=5)))
    st.plotly_chart(clean_chart(fig_em, y_suffix="%"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r3_c4:
    npm_vals = calc_margin_series(net_inc)
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Net Profit Margin</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_npm", help="Vollbild / Details"):
            open_detail_modal("Net Profit Margin (%)", npm_vals, is_pct=True, color="#ef4444", chart_type="scatter", description="Nettogewinnmarge: Wie viel Cent je Dollar/Euro Umsatz als Reingewinn verbleiben.")
    fig_npm = go.Figure(go.Scatter(x=date_labels, y=npm_vals, mode='lines+markers', line=dict(color="#ef4444", width=2.2), marker=dict(size=5)))
    st.plotly_chart(clean_chart(fig_npm, y_suffix="%"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# REIHE 4: BILANZ & VERSCHULDUNG
# ==============================================================================
st.markdown('<div class="section-label">Bilanz, Liquidität & Verschuldung</div>', unsafe_allow_html=True)
r4_c1, r4_c2, r4_c3, r4_c4 = st.columns(4)

with r4_c1:
    td_vals = [total_debt.get(y, 0)/1e9 for y in cols_chrono]
    cash_vals = [cash.get(y, 0)/1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Debt vs. Cash</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_dvc", help="Vollbild / Details"):
            open_detail_modal("Gesamtschulden vs. Liquidität", td_vals, is_pct=False, unit_suffix="B", color="#ef4444", chart_type="bar", description="Gegenüberstellung von Gesamtschulden und liquiden Mitteln.")
    fig_debt_cash = go.Figure()
    fig_debt_cash.add_trace(go.Bar(x=date_labels, y=td_vals, name="Debt", marker_color="#ef4444"))
    fig_debt_cash.add_trace(go.Bar(x=date_labels, y=cash_vals, name="Cash", marker_color="#22c55e"))
    fig_debt_cash.update_layout(barmode="group")
    st.plotly_chart(clean_chart(fig_debt_cash, y_prefix="$", y_suffix="B", show_legend=True), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r4_c2:
    nd_vals = [net_debt.get(y, 0)/1e9 for y in cols_chrono]
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Net Debt</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_nd", help="Vollbild / Details"):
            open_detail_modal("Net Debt (Nettoschulden)", nd_vals, is_pct=False, unit_suffix="B", color="#0f172a", chart_type="bar", description="Nettoschulden (Gesamtverschuldung abzüglich liquider Mittel). Negative Werte bedeuten eine Netto-Cash-Position.")
    fig_nd = go.Figure(go.Bar(x=date_labels, y=nd_vals, marker_color="#0f172a", width=0.45))
    st.plotly_chart(clean_chart(fig_nd, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r4_c3:
    de_vals = []
    for y in cols_chrono:
        eq = equity.get(y, np.nan)
        td = total_debt.get(y, np.nan)
        de_vals.append((td / eq) if pd.notnull(eq) and eq != 0 else 0)
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Debt-to-Equity</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_de", help="Vollbild / Details"):
            open_detail_modal("Debt-to-Equity Ratio", de_vals, is_pct=False, unit_suffix="x", color="#8b5cf6", chart_type="scatter", description="Verschuldungsgrad im Verhältnis zum buchhalterischen Eigenkapital.")
    fig_de = go.Figure(go.Scatter(x=date_labels, y=de_vals, mode='lines+markers', line=dict(color="#8b5cf6", width=2.2), marker=dict(size=5)))
    st.plotly_chart(clean_chart(fig_de, y_suffix="x"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r4_c4:
    nd_ebitda_vals = []
    for y in cols_chrono:
        eb = ebitda.get(y, np.nan)
        nd = net_debt.get(y, np.nan)
        nd_ebitda_vals.append((nd / eb) if pd.notnull(eb) and eb != 0 else 0)
    st.markdown('<div class="metric-card-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown('<span class="metric-card-title">Net Debt / EBITDA</span>', unsafe_allow_html=True)
    with h_col2:
        if st.button("↗", key="btn_nd_eb", help="Vollbild / Details"):
            open_detail_modal("Net Debt / EBITDA", nd_ebitda_vals, is_pct=False, unit_suffix="x", color="#0284c7", chart_type="scatter", description="Schuldendeckungsgrad: Zeigt, wie viele Jahre an operativem EBITDA nötig wären, um die Nettoschulden vollständig zu tilgen.")
    fig_nd_eb = go.Figure(go.Scatter(x=date_labels, y=nd_ebitda_vals, mode='lines+markers', line=dict(color="#0284c7", width=2.2), marker=dict(size=5)))
    st.plotly_chart(clean_chart(fig_nd_eb, y_suffix="x"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# TAB-ÜBERSICHT: ALLE DETAILTABELLEN
# ==============================================================================
tabs = st.tabs([
    "📈 Margenprofil & GuV",
    "🏛️ Bilanz & Verschuldung",
    "💸 Cashflow-Rechnung",
    "⚖️ Valuation Multiples",
    "🎁 Dividenden",
    "🎯 DCF & Analysten"
])

def format_df(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    res.columns = [
        pd.to_datetime(c).strftime("Q%q '%y") if is_quarterly else pd.to_datetime(c).strftime("%Y-%m-%d")
        for c in res.columns
    ]
    for col in res.columns:
        res[col] = res[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else ("N/A" if pd.isna(x) else x))
    return res

with tabs[0]:
    col_t1, col_t2 = st.columns([1, 1])
    with col_t1:
        st.write("**Margenverlauf (%)**")
        fig_m = go.Figure()
        for label, series, color in [
            ("Gross Margin", (gp / rev) * 100, "#d97706"),
            ("Operating Margin", (ebit / rev) * 100, "#64748b"),
            ("EBITDA Margin", (ebitda / rev) * 100, "#3b82f6"),
            ("Net Profit Margin", (net_inc / rev) * 100, "#ef4444")
        ]:
            fig_m.add_trace(go.Scatter(x=date_labels, y=[series.get(y, np.nan) for y in cols_chrono], mode='lines+markers', name=label, line=dict(color=color, width=2)))
        fig_m.update_layout(height=280, margin=dict(l=40, r=10, t=10, b=30), template="plotly_white")
        st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False})
    
    with col_t2:
        st.write("**Gewinn- und Verlustrechnung (GuV)**")
        df_inc = pd.DataFrame({
            "Revenue (Umsatz)": rev,
            "Gross Profit (Bruttogewinn)": gp,
            "Operating Income (EBIT)": ebit,
            "EBITDA": ebitda,
            "Net Income (Nettogewinn)": net_inc
        }).T
        st.dataframe(format_df(df_inc), use_container_width=True)

with tabs[1]:
    b_c1, b_c2 = st.columns([1, 1])
    with b_c1:
        st.write("**Bilanz- & Verschuldungskennzahlen**")
        df_bs = pd.DataFrame({
            "Total Assets": total_assets,
            "Total Liabilities": total_liab,
            "Cash & Equivalents": cash,
            "Short-Term Debt": st_debt,
            "Long-Term Debt": lt_debt,
            "Total Debt": total_debt,
            "Net Debt": net_debt
        }).T
        st.dataframe(format_df(df_bs), use_container_width=True)

    with b_c2:
        st.write("**Verschuldungsgrade & Deckung**")
        ratios_bs = pd.DataFrame(index=["Debt-to-Equity", "Net Debt / EBITDA"], columns=cols_chrono)
        for y in cols_chrono:
            eq = equity.get(y, np.nan)
            eb = ebitda.get(y, np.nan)
            td = total_debt.get(y, np.nan)
            nd = net_debt.get(y, np.nan)
            ratios_bs.loc["Debt-to-Equity", y] = f"{(td/eq):.2f}x" if pd.notnull(eq) and eq != 0 else "N/A"
            ratios_bs.loc["Net Debt / EBITDA", y] = f"{(nd/eb):.2f}x" if pd.notnull(eb) and eb != 0 else "N/A"
        ratios_bs.columns = [
            pd.to_datetime(c).strftime("Q%q '%y") if is_quarterly else pd.to_datetime(c).strftime("%Y-%m-%d")
            for c in ratios_bs.columns
        ]
        st.dataframe(ratios_bs, use_container_width=True)

with tabs[2]:
    cf_c1, cf_c2 = st.columns([1, 1])
    with cf_c1:
        st.write("**Free Cash Flow Rendite (FCF Yield)**")
        fcf_yield_vals = [((fcf.get(y, 0) / m_cap) * 100) if pd.notnull(m_cap) and m_cap > 0 else 0 for y in cols_chrono]
        fig_fy = go.Figure(go.Bar(x=date_labels, y=fcf_yield_vals, marker_color="#0d9488", width=0.45))
        st.plotly_chart(clean_chart(fig_fy, y_suffix="%"), use_container_width=True, config={'displayModeBar': False})

    with cf_c2:
        st.write("**Cashflow-Entwicklung**")
        df_cf = pd.DataFrame({
            "Operating Cash Flow": ocf,
            "Capital Expenditures (CapEx)": capex,
            "Free Cash Flow": fcf
        }).T
        st.dataframe(format_df(df_cf), use_container_width=True)

with tabs[3]:
    v_c1, v_c2 = st.columns(2)
    with v_c1:
        st.write("**Multiples & Bewertungsmetriken**")
        latest_fcf = fcf.iloc[-1] if not fcf.empty else np.nan
        p_fcf = (m_cap / latest_fcf) if pd.notnull(m_cap) and pd.notnull(latest_fcf) and latest_fcf > 0 else "N/A"

        st.dataframe(pd.DataFrame({
            "Bewertungskennzahl": ["Marktkapitalisierung", "Trailing P/E (KGV)", "Forward P/E", "P/FCF Ratio", "EV / EBITDA", "Ausstehende Aktien"],
            "Wert": [
                f"{m_cap:,.0f} {currency}" if pd.notnull(m_cap) else "N/A",
                f"{info.get('trailingPE', 0):.2f}" if info.get('trailingPE') else "N/A",
                f"{info.get('forwardPE', 0):.2f}" if info.get('forwardPE') else "N/A",
                f"{p_fcf:.2f}" if isinstance(p_fcf, (int, float)) else "N/A",
                f"{info.get('enterpriseToEbitda', 0):.2f}" if info.get('enterpriseToEbitda') else "N/A",
                f"{shares:,.0f}"
            ]
        }), use_container_width=True)

    with v_c2:
        st.write("**Gewinnkennzahlen (EPS)**")
        st.dataframe(pd.DataFrame({
            "Kennzahl": ["Trailing EPS (LTM)", "Forward EPS", "Buchwert je Aktie (Book Value)"],
            "Wert": [
                f"{info.get('trailingEps', 0):.2f} {currency}",
                f"{info.get('forwardEps', 0):.2f} {currency}",
                f"{info.get('bookValue', 0):.2f} {currency}"
            ]
        }), use_container_width=True)

with tabs[4]:
    if not dividends.empty:
        d_c1, d_c2 = st.columns(2)
        annual_div = dividends.resample('YE').sum()
        with d_c1:
            st.write("**Dividenden-Historie (letzte 8 Jahre)**")
            fig_div = go.Figure(go.Bar(
                x=[d.strftime("%Y") for d in annual_div.index[-8:]],
                y=annual_div.values[-8:],
                marker_color="#8b5cf6",
                width=0.45
            ))
            st.plotly_chart(clean_chart(fig_div, y_prefix="$"), use_container_width=True, config={'displayModeBar': False})
        with d_c2:
            st.write("**Ausschüttungskennzahlen**")
            div_yield = info.get("dividendYield")
            st.dataframe(pd.DataFrame({
                "Dividenden-Metrik": ["Dividendenrendite", "Payout Ratio (Gewinn)", "Jahresdividende"],
                "Wert": [
                    f"{div_yield * 100:.2f}%" if div_yield else "0.00%",
                    f"{info.get('payoutRatio', 0) * 100:.2f}%" if info.get('payoutRatio') else "N/A",
                    f"{info.get('dividendRate', 0):.2f} {currency}"
                ]
            }), use_container_width=True)
    else:
        st.info("Dieses Wertpapier zahlt derzeit keine Dividenden aus.")

with tabs[5]:
    dcf_c1, dcf_c2 = st.columns(2)
    with dcf_c1:
        st.write("**Konsens & Kursziele der Analysten**")
        st.dataframe(pd.DataFrame({
            "Analysten-Metrik": ["Empfehlung", "Kursziel Durchschnitt", "Kursziel Hoch", "Kursziel Tief", "Anzahl Analysten"],
            "Wert": [
                str(info.get("recommendationKey", "N/A")).upper(),
                f"{info.get('targetMeanPrice', 0):,.2f} {currency}",
                f"{info.get('targetHighPrice', 0):,.2f} {currency}",
                f"{info.get('targetLowPrice', 0):,.2f} {currency}",
                str(info.get("numberOfAnalystOpinions", "N/A"))
            ]
        }), use_container_width=True)

    with dcf_c2:
        st.write("**DCF Baseline & WACC Parameter**")
        beta = info.get("beta", 1.0) or 1.0
        rf_rate = 4.25
        erp = 5.0
        st.dataframe(pd.DataFrame({
            "Modell-Parameter": ["Beta (Marktrisiko)", "Risk-Free Rate (Rf)", "Equity Risk Premium (ERP)", "Eigenkapitalkosten (CAPM)", "Empf. Terminal Growth Rate"],
            "Wert": [f"{beta:.2f}", f"{rf_rate:.2f}%", f"{erp:.2f}%", f"{rf_rate + (beta * erp):.2f}%", "2.0% - 2.5%"]
        }), use_container_width=True)
