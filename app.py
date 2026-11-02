import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Financial Analytics Terminal", layout="wide", initial_sidebar_state="collapsed")

# 1. Custom CSS für ein aufgeräumtes Terminal-Design
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 96% !important;
    }
    
    /* Top Bar Header */
    .top-header-box {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #ffffff;
        padding: 16px 24px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .company-title {
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
    }
    .company-meta {
        font-size: 13px;
        color: #64748b;
        margin-top: 4px;
    }

    /* KPI Card Container */
    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 12px 14px 6px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        margin-bottom: 12px;
    }
    .metric-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
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
        padding: 1.5px 5px;
        border-radius: 4px;
    }
    .price-badge-up {
        background-color: #dcfce7;
        color: #15803d;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
    }
    .price-badge-down {
        background-color: #fee2e2;
        color: #b91c1c;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
    }

    /* Tabellen */
    div[data-testid="stDataFrame"] {
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        padding: 6px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Ticker-Suche
def resolve_ticker(query: str) -> str:
    query = query.strip()
    if not query:
        return "AAPL"
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

# 3. Header-Bereich mit sauberer Suchleiste
top_c1, top_c2, top_c3 = st.columns([3, 1.2, 0.8])
with top_c1:
    search_input = st.text_input("Ticker oder Firmenname", value="Apple", label_visibility="collapsed", placeholder="Suche (z.B. Microsoft, NVDA, Tesla)...")
with top_c2:
    period_type = st.radio("Zeitraum", ["Jährlich", "Quartal"], horizontal=True, label_visibility="collapsed")
with top_c3:
    refresh_btn = st.button("Aktualisieren", use_container_width=True)

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

# Info Header Banner
company_name = info.get("longName", symbol)
sector = info.get("sector", "N/A")
industry = info.get("industry", "N/A")
currency = info.get("currency", "USD")
curr_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)

st.markdown(f"""
<div class="top-header-box">
    <div>
        <div class="company-title">{company_name} ({symbol})</div>
        <div class="company-meta">{sector} • {industry} • Währung in {currency}</div>
    </div>
    <div style="text-align: right;">
        <div style="font-size: 22px; font-weight: 700; color: #0f172a;">{curr_price:,.2f} {currency}</div>
        <div style="font-size: 12px; color: #64748b;">Market Cap: {info.get('marketCap', 0)/1e9:,.1f}B</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. Plotly Helper-Funktion (ohne störende Menüleiste)
def clean_chart(fig, y_prefix="", y_suffix=""):
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=42, r=10, t=10, b=35),
        height=190,
        showlegend=False,
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
    # Fallback-Suche
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

# Kursentwicklung 1Y
price_chg = 0.0
if not hist.empty and len(hist) > 1:
    price_chg = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100

# ==============================================================================
# REIHE 1: Price, Revenue, Gross Profit, Operating Income
# ==============================================================================
r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)

with r1_c1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    badge_cls = "price-badge-up" if price_chg >= 0 else "price-badge-down"
    arrow = "↑" if price_chg >= 0 else "↓"
    st.markdown(f'<div class="metric-card-header"><span class="metric-card-title">Price <span class="{badge_cls}">{arrow} {price_chg:+.2f}%</span></span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    if not hist.empty:
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', line=dict(color="#16a34a", width=1.8), fill='tozeroy', fillcolor='rgba(22, 163, 74, 0.1)'))
        st.plotly_chart(clean_chart(fig_p, y_prefix="$"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r1_c2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-card-header"><span class="metric-card-title">Revenue</span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    fig_r = go.Figure(go.Bar(x=date_labels, y=[rev.get(y, 0) / 1e9 for y in cols_chrono], marker_color="#ea580c", width=0.45))
    st.plotly_chart(clean_chart(fig_r, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r1_c3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-card-header"><span class="metric-card-title"><span class="kpi-badge">KPI</span> Gross Profit</span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    fig_g = go.Figure(go.Bar(x=date_labels, y=[gp.get(y, 0) / 1e9 for y in cols_chrono], marker_color="#d97706", width=0.45))
    st.plotly_chart(clean_chart(fig_g, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r1_c4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-card-header"><span class="metric-card-title"><span class="kpi-badge">KPI</span> Operating Income</span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    fig_eb = go.Figure(go.Bar(x=date_labels, y=[ebit.get(y, 0) / 1e9 for y in cols_chrono], marker_color="#64748b", width=0.45))
    st.plotly_chart(clean_chart(fig_eb, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# REIHE 2: EBITDA, Net Income, Free Cash Flow, EPS
# ==============================================================================
r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)

with r2_c1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-card-header"><span class="metric-card-title">EBITDA</span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    fig_ebitda = go.Figure(go.Bar(x=date_labels, y=[ebitda.get(y, 0) / 1e9 for y in cols_chrono], marker_color="#93c5fd", width=0.45))
    st.plotly_chart(clean_chart(fig_ebitda, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r2_c2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-card-header"><span class="metric-card-title">Net Income</span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    fig_ni = go.Figure(go.Bar(x=date_labels, y=[net_inc.get(y, 0) / 1e9 for y in cols_chrono], marker_color="#fca5a5", width=0.45))
    st.plotly_chart(clean_chart(fig_ni, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r2_c3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-card-header"><span class="metric-card-title">Free Cash Flow</span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    fig_f = go.Figure(go.Bar(x=date_labels, y=[fcf.get(y, 0) / 1e9 for y in cols_chrono], marker_color="#b45309", width=0.45))
    st.plotly_chart(clean_chart(fig_f, y_prefix="$", y_suffix="B"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with r2_c4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-card-header"><span class="metric-card-title">EPS</span><span style="color:#94a3b8; font-size:12px;">↗</span></div>', unsafe_allow_html=True)
    eps_vals = [net_inc.get(y, 0) / shares for y in cols_chrono]
    fig_e = go.Figure(go.Bar(x=date_labels, y=eps_vals, marker_color="#facc15", width=0.45))
    st.plotly_chart(clean_chart(fig_e, y_prefix="$"), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# TAB-ÜBERSICHT: DETAILS, MARGEN, BILANZ, BEWERTUNG & DCF
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
    total_assets = get_row("Total Assets", balance_sheet)
    total_liab = get_row("Total Liabilities Net Minority Interest", balance_sheet)
    cash = get_row("Cash And Cash Equivalents", balance_sheet)
    st_debt = get_row("Current Debt", balance_sheet)
    lt_debt = get_row("Long Term Debt", balance_sheet)
    total_debt = st_debt.fillna(0) + lt_debt.fillna(0)
    net_debt = total_debt - cash.fillna(0)
    equity = get_row("Stockholders Equity", balance_sheet)

    b_c1, b_c2 = st.columns([1, 1])
    with b_c1:
        st.write("**Verschuldungsstruktur (Mrd.)**")
        fig_debt = go.Figure()
        fig_debt.add_trace(go.Bar(x=date_labels, y=[total_debt.get(y, 0)/1e9 for y in cols_chrono], name="Total Debt", marker_color="#ef4444"))
        fig_debt.add_trace(go.Bar(x=date_labels, y=[cash.get(y, 0)/1e9 for y in cols_chrono], name="Cash", marker_color="#22c55e"))
        fig_debt.add_trace(go.Scatter(x=date_labels, y=[net_debt.get(y, 0)/1e9 for y in cols_chrono], mode='lines+markers', name="Net Debt", line=dict(color="#0f172a", width=2)))
        fig_debt.update_layout(height=280, margin=dict(l=40, r=10, t=10, b=30), template="plotly_white", barmode="group")
        st.plotly_chart(fig_debt, use_container_width=True, config={'displayModeBar': False})

    with b_c2:
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

with tabs[2]:
    cf_c1, cf_c2 = st.columns([1, 1])
    with cf_c1:
        st.write("**Free Cash Flow Rendite (FCF Yield)**")
        m_cap = info.get("marketCap", np.nan)
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
        m_cap = info.get("marketCap", np.nan)
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
