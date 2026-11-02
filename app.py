import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Financial Analytics Terminal", layout="wide", initial_sidebar_state="collapsed")

# 1. Custom CSS für das moderne Card-Grid-Design
st.markdown("""
<style>
    /* Hintergrund & Grundtypografie */
    .stApp {
        background-color: #f3f4f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Hauptcontainer-Abstände minimieren */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 95%;
    }

    /* KPI Card Header Styling */
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

    /* Dataframe-Styling */
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

# Suchleiste
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
        margin=dict(l=42, r=12, t=10, b=45),
        height=210,
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            linecolor="#e5e7eb",
            tickangle=-45,
            tickfont=dict(size=10, color="#6b7280")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f3f4f6",
            gridwidth=1,
            linecolor="transparent",
            tickfont=dict(size=10, color="#6b7280"),
            tickprefix=y_prefix,
            ticksuffix=y_suffix
        )
    )
    return fig

# Zeitreihen & Metrik-Extraktion
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

# ==============================================================================
# REIHE 1: VISUELLES KARTEN-RASTER (Card Grid wie im Screenshot)
# ==============================================================================
c1, c2, c3, c4 = st.columns(4)

# 1. Price Area Chart
with c1:
    st.markdown(f"""
    <div class="metric-card-header">
        <span class="metric-card-title">Price <span class="price-change-badge">{'↑' if price_change_pct >= 0 else '↓'} {price_change_pct:+.2f}%</span></span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    if not hist.empty:
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(
            x=hist.index, y=hist['Close'],
            mode='lines',
            line=dict(color="#16a34a", width=1.8),
            fill='tozeroy',
            fillcolor='rgba(22, 163, 74, 0.12)'
        ))
        st.plotly_chart(build_clean_chart(fig_price, y_prefix="$"), use_container_width=True)

# 2. Revenue (Warm Orange/Amber Bar Chart)
with c2:
    st.markdown("""
    <div class="metric-card-header">
        <span class="metric-card-title">Revenue</span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    fig_rev = go.Figure()
    fig_rev.add_trace(go.Bar(
        x=date_labels, y=[rev.get(y, 0) / 1e9 for y in years],
        marker_color="#e08a3c",
        width=0.45
    ))
    st.plotly_chart(build_clean_chart(fig_rev, y_prefix="$", y_suffix="B"), use_container_width=True)

# 3. Gross Profit (KPI Stack/Comparison)
with c3:
    st.markdown("""
    <div class="metric-card-header">
        <span class="metric-card-title"><span class="kpi-pill">KPI</span> Gross Profit</span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    gp = get_row("Gross Profit", financials)
    fig_gp = go.Figure()
    fig_gp.add_trace(go.Bar(
        x=date_labels, y=[gp.get(y, 0) / 1e9 for y in years],
        marker_color="#c27838",
        width=0.45
    ))
    st.plotly_chart(build_clean_chart(fig_gp, y_prefix="$", y_suffix="B"), use_container_width=True)

# 4. Operating Income / EBIT (Slate / Blue-Grey)
with c4:
    st.markdown("""
    <div class="metric-card-header">
        <span class="metric-card-title"><span class="kpi-pill">KPI</span> Operating Income</span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    ebit = get_row("Operating Income", financials)
    fig_ebit = go.Figure()
    fig_ebit.add_trace(go.Bar(
        x=date_labels, y=[ebit.get(y, 0) / 1e9 for y in years],
        marker_color="#64748b",
        width=0.45
    ))
    st.plotly_chart(build_clean_chart(fig_ebit, y_prefix="$", y_suffix="B"), use_container_width=True)

# ==============================================================================
# REIHE 2: EBITDA, NET INCOME, FCF, EPS (Farben exakt aus dem Screenshot)
# ==============================================================================
r2_1, r2_2, r2_3, r2_4 = st.columns(4)

# 5. EBITDA (Light Blue Bar Chart)
with r2_1:
    st.markdown("""
    <div class="metric-card-header">
        <span class="metric-card-title">EBITDA</span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    fig_ebitda = go.Figure()
    fig_ebitda.add_trace(go.Bar(
        x=date_labels, y=[ebitda.get(y, 0) / 1e9 for y in years],
        marker_color="#93c5fd",
        width=0.45
    ))
    st.plotly_chart(build_clean_chart(fig_ebitda, y_prefix="$", y_suffix="B"), use_container_width=True)

# 6. Net Income (Soft Salmon / Orange Bar Chart)
with r2_2:
    st.markdown("""
    <div class="metric-card-header">
        <span class="metric-card-title">Net Income</span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    fig_ni = go.Figure()
    fig_ni.add_trace(go.Bar(
        x=date_labels, y=[net_inc.get(y, 0) / 1e9 for y in years],
        marker_color="#fca5a5",
        width=0.45
    ))
    st.plotly_chart(build_clean_chart(fig_ni, y_prefix="$", y_suffix="B"), use_container_width=True)

# 7. Free Cash Flow (Golden Amber Bar Chart)
with r2_3:
    st.markdown("""
    <div class="metric-card-header">
        <span class="metric-card-title">Free Cash Flow</span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    fig_fcf = go.Figure()
    fig_fcf.add_trace(go.Bar(
        x=date_labels, y=[fcf.get(y, 0) / 1e9 for y in years],
        marker_color="#d97706",
        width=0.45
    ))
    st.plotly_chart(build_clean_chart(fig_fcf, y_prefix="$", y_suffix="B"), use_container_width=True)

# 8. EPS (Soft Yellow/Gold Bar Chart)
with r2_4:
    st.markdown("""
    <div class="metric-card-header">
        <span class="metric-card-title">EPS</span>
        <span style="color:#9ca3af; font-size:12px;">↗</span>
    </div>
    """, unsafe_allow_html=True)
    shares = info.get("sharesOutstanding", 1) or 1
    eps_vals = [net_inc.get(y, 0) / shares for y in years]
    fig_eps = go.Figure()
    fig_eps.add_trace(go.Bar(
        x=date_labels, y=eps_vals,
        marker_color="#fde047",
        width=0.45
    ))
    st.plotly_chart(build_clean_chart(fig_eps, y_prefix="$"), use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# DETAILTABELLEN & DEEP DIVE (Integrierte Fundamentaldaten)
# ==============================================================================
tabs = st.tabs(["📑 GuV & Margen", "🏛️ Bilanz & Schulden", "💸 Cashflow & FCF", "⚖️ Bewertung & DCF", "🎁 Dividenden"])

def format_df(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    res.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") if isinstance(c, (pd.Timestamp, str)) else str(c) for c in res.columns]
    for col in res.columns:
        res[col] = res[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else ("N/A" if pd.isna(x) else x))
    return res

with tabs[0]:
    t1, t2 = st.columns(2)
    with t1:
        st.write("**Gewinn- und Verlustrechnung (in Währung)**")
        df_inc = pd.DataFrame({
            "Revenue (Umsatz)": rev,
            "Gross Profit": gp,
            "Operating Income (EBIT)": ebit,
            "EBITDA": ebitda,
            "Net Income (Nettogewinn)": net_inc
        }).T
        st.dataframe(format_df(df_inc), use_container_width=True)
    with t2:
        st.write("**Margenprofil (%)**")
        margins = pd.DataFrame(index=["Gross Margin", "Operating Margin", "EBITDA Margin", "Net Margin"], columns=years)
        for y in years:
            r = rev.get(y, np.nan)
            if pd.notnull(r) and r != 0:
                margins.loc["Gross Margin", y] = f"{(gp.get(y, 0)/r)*100:.2f}%"
                margins.loc["Operating Margin", y] = f"{(ebit.get(y, 0)/r)*100:.2f}%"
                margins.loc["EBITDA Margin", y] = f"{(ebitda.get(y, 0)/r)*100:.2f}%"
                margins.loc["Net Margin", y] = f"{(net_inc.get(y, 0)/r)*100:.2f}%"
        margins.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in margins.columns]
        st.dataframe(margins, use_container_width=True)

with tabs[1]:
    t_bs1, t_bs2 = st.columns(2)
    total_assets = get_row("Total Assets", balance_sheet)
    total_liab = get_row("Total Liabilities Net Minority Interest", balance_sheet)
    cash = get_row("Cash And Cash Equivalents", balance_sheet)
    st_debt = get_row("Current Debt", balance_sheet)
    lt_debt = get_row("Long Term Debt", balance_sheet)
    total_debt = st_debt.fillna(0) + lt_debt.fillna(0)
    net_debt = total_debt - cash.fillna(0)
    equity = get_row("Stockholders Equity", balance_sheet)

    with t_bs1:
        st.write("**Bilanzpositionen**")
        df_bs = pd.DataFrame({
            "Total Assets": total_assets,
            "Total Liabilities": total_liab,
            "Cash & Equivalents": cash,
            "Total Debt": total_debt,
            "Net Debt": net_debt
        }).T
        st.dataframe(format_df(df_bs), use_container_width=True)
    with t_bs2:
        st.write("**Verschuldungsgrade**")
        ratios_bs = pd.DataFrame(index=["Debt-to-Equity", "Net Debt / EBITDA"], columns=balance_sheet.columns)
        for y in balance_sheet.columns:
            eq = equity.get(y, np.nan)
            eb = ebitda.get(y, np.nan)
            td = total_debt.get(y, np.nan)
            nd = net_debt.get(y, np.nan)
            ratios_bs.loc["Debt-to-Equity", y] = f"{(td/eq):.2f}x" if pd.notnull(eq) and eq != 0 else "N/A"
            ratios_bs.loc["Net Debt / EBITDA", y] = f"{(nd/eb):.2f}x" if pd.notnull(eb) and eb != 0 else "N/A"
        ratios_bs.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in ratios_bs.columns]
        st.dataframe(ratios_bs, use_container_width=True)

with tabs[2]:
    market_cap = info.get("marketCap", np.nan)
    t_cf1, t_cf2 = st.columns(2)
    with t_cf1:
        st.write("**Cashflow-Entwicklung**")
        df_cf = pd.DataFrame({
            "Operating Cash Flow": ocf,
            "Capital Expenditures (CapEx)": capex,
            "Free Cash Flow": fcf
        }).T
        st.dataframe(format_df(df_cf), use_container_width=True)
    with t_cf2:
        st.write("**FCF Yield (aktuelle Bewertung)**")
        fcf_yield_row = pd.DataFrame(index=["FCF Yield"], columns=cashflow.columns)
        for y in cashflow.columns:
            curr_fcf = fcf.get(y, np.nan)
            fcf_yield_row.loc["FCF Yield", y] = f"{(curr_fcf/market_cap)*100:.2f}%" if pd.notnull(curr_fcf) and pd.notnull(market_cap) else "N/A"
        fcf_yield_row.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in fcf_yield_row.columns]
        st.dataframe(fcf_yield_row, use_container_width=True)

with tabs[3]:
    t_v1, t_v2 = st.columns(2)
    with t_v1:
        st.write("**Bewertungs-Multiples**")
        st.dataframe(pd.DataFrame({
            "Metrik": ["Market Cap", "Trailing P/E", "Forward P/E", "EV/EBITDA", "Trailing EPS", "Forward EPS"],
            "Wert": [
                f"{market_cap:,.0f} {info.get('currency', '')}" if pd.notnull(market_cap) else "N/A",
                f"{info.get('trailingPE', 0):.2f}" if info.get('trailingPE') else "N/A",
                f"{info.get('forwardPE', 0):.2f}" if info.get('forwardPE') else "N/A",
                f"{info.get('enterpriseToEbitda', 0):.2f}" if info.get('enterpriseToEbitda') else "N/A",
                f"{info.get('trailingEps', 0):.2f}" if info.get('trailingEps') else "N/A",
                f"{info.get('forwardEps', 0):.2f}" if info.get('forwardEps') else "N/A"
            ]
        }), use_container_width=True)
    with t_v2:
        st.write("**DCF Baseline & Analysten**")
        beta = info.get("beta", 1.0) or 1.0
        rf, erp = 4.25, 5.0
        st.dataframe(pd.DataFrame({
            "Parameter": ["Beta", "Risk-Free Rate (Rf)", "Equity Risk Premium", "Cost of Equity (CAPM)", "Kursziel Ø Konsens"],
            "Wert": [f"{beta:.2f}", f"{rf:.2f}%", f"{erp:.2f}%", f"{rf + (beta * erp):.2f}%", f"{info.get('targetMeanPrice', 0):,.2f}"]
        }), use_container_width=True)

with tabs[4]:
    if not dividends.empty:
        annual_div = dividends.resample('YE').sum()
        d1, d2 = st.columns(2)
        with d1:
            div_yield = info.get("dividendYield")
            st.dataframe(pd.DataFrame({
                "Kennzahl": ["Dividend Yield", "Payout Ratio", "Dividend Rate"],
                "Wert": [
                    f"{div_yield * 100:.2f}%" if div_yield else "0.00%",
                    f"{info.get('payoutRatio', 0) * 100:.2f}%" if info.get('payoutRatio') else "N/A",
                    f"{info.get('dividendRate', 0):.2f} {info.get('currency', '')}" if info.get('dividendRate') else "0.00"
                ]
            }), use_container_width=True)
        with d2:
            st.write("**Dividenden je Aktie (letzte Jahre)**")
            df_div_hist = pd.DataFrame(annual_div.tail(5)).rename(columns={"Dividends": "Ausschüttung"})
            df_div_hist.index = [d.strftime("%Y") for d in df_div_hist.index]
            st.dataframe(df_div_hist, use_container_width=True)
    else:
        st.info("Dieses Wertpapier zahlt keine Dividenden aus.")
