import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Financial Metrics Dashboard", layout="wide")

st.title("📊 Financial Metrics & Valuation Explorer")
st.caption("Umfassende Fundamentalanalyse, Bilanzdaten, interaktive Diagramme & DCF-Metriken")

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

col_input, col_btn = st.columns([4, 1])
with col_input:
    user_query = st.text_input("Geben Sie ein Tickersymbol oder einen Unternehmensnamen ein:", value="Apple")
with col_btn:
    st.write("")
    search_clicked = st.button("Analysieren", use_container_width=True)

ticker_symbol = resolve_ticker(user_query)

if ticker_symbol:
    ticker = yf.Ticker(ticker_symbol)
    
    with st.spinner(f"Lade Finanzdaten für {ticker_symbol}..."):
        try:
            info = ticker.info or {}
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            dividends = ticker.dividends
        except Exception as e:
            st.error(f"Fehler beim Abrufen der Marktdaten: {e}")
            st.stop()

    if not info or financials.empty:
        st.warning(f"Keine ausreichenden Daten für '{user_query}' (Symbol: {ticker_symbol}) gefunden.")
        st.stop()

    # Stammdaten Header
    st.subheader(f"{info.get('longName', ticker_symbol)} ({ticker_symbol})")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Sektor", info.get("sector", "N/A"))
    m_col2.metric("Industrie", info.get("industry", "N/A"))
    m_col3.metric("Währung", info.get("currency", "USD"))
    curr_price = info.get("currentPrice") or info.get("regularMarketPrice")
    m_col4.metric("Aktueller Kurs", f"{curr_price:,.2f} {info.get('currency', '')}" if curr_price else "N/A")

    st.markdown("---")

    def format_df(df: pd.DataFrame) -> pd.DataFrame:
        formatted = df.copy()
        formatted.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") if isinstance(c, (pd.Timestamp, str)) else str(c) for c in formatted.columns]
        for col in formatted.columns:
            formatted[col] = formatted[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else ("N/A" if pd.isna(x) else x))
        return formatted

    years = sorted(financials.columns)  # Chronologisch für Charts von alt nach neu

    def get_fin(key, df):
        return df.loc[key] if key in df.index else pd.Series(index=df.columns, dtype=float)

    rev = get_fin("Total Revenue", financials)
    gross_profit = get_fin("Gross Profit", financials)
    ebit = get_fin("Operating Income", financials)
    net_income = get_fin("Net Income", financials)
    ebitda = get_fin("EBITDA", financials)

    # 1. GuV & Margen
    st.markdown("### 1. Gewinn- und Verlustrechnung (Income Statement) & Margen")
    
    # Diagramm: Umsatz & Net Income Trend
    years_str = [pd.to_datetime(y).strftime("%Y") for y in years]
    rev_vals = [rev.get(y, 0) / 1e9 for y in years]
    net_vals = [net_income.get(y, 0) / 1e9 for y in years]
    ebitda_vals = [ebitda.get(y, 0) / 1e9 for y in years]

    fig_is = go.Figure()
    fig_is.add_trace(go.Bar(x=years_str, y=rev_vals, name="Umsatz (Mrd.)", marker_color="#2563eb"))
    fig_is.add_trace(go.Bar(x=years_str, y=ebitda_vals, name="EBITDA (Mrd.)", marker_color="#06b6d4"))
    fig_is.add_trace(go.Bar(x=years_str, y=net_vals, name="Nettogewinn (Mrd.)", marker_color="#10b981"))
    fig_is.update_layout(barmode='group', title="Historische Ertragsentwicklung (in Milliarden)", margin=dict(t=40, b=20, l=20, r=20), height=350)
    st.plotly_chart(fig_is, use_container_width=True)

    # Margenberechnung (%)
    margins = pd.DataFrame(index=[
        "Gross Margin (%)",
        "Operating Margin (%)",
        "EBITDA Margin (%)",
        "Net Profit Margin (%)"
    ], columns=years)

    for y in years:
        r = rev.get(y, np.nan)
        if pd.notnull(r) and r != 0:
            margins.loc["Gross Margin (%)", y] = (gross_profit.get(y, np.nan) / r) * 100
            margins.loc["Operating Margin (%)", y] = (ebit.get(y, np.nan) / r) * 100
            margins.loc["EBITDA Margin (%)", y] = (ebitda.get(y, np.nan) / r) * 100
            margins.loc["Net Profit Margin (%)", y] = (net_income.get(y, np.nan) / r) * 100

    col_is1, col_is2 = st.columns(2)
    with col_is1:
        st.write("**Absolute Zahlen (in Originalwährung)**")
        df_inc = pd.DataFrame({
            "Revenue (Umsatz)": rev,
            "Gross Profit (Bruttogewinn)": gross_profit,
            "Operating Income / EBIT": ebit,
            "EBITDA": ebitda,
            "Net Income (Nettogewinn)": net_income
        }).T
        st.dataframe(format_df(df_inc), use_container_width=True)

    with col_is2:
        # Liniendiagramm für Margenverlauf
        fig_margin = go.Figure()
        for m_name in margins.index:
            fig_margin.add_trace(go.Scatter(x=years_str, y=margins.loc[m_name], mode='lines+markers', name=m_name.replace(" (%)", "")))
        fig_margin.update_layout(title="Margenprofil über Zeit (%)", margin=dict(t=40, b=20, l=20, r=20), height=320)
        st.plotly_chart(fig_margin, use_container_width=True)

    # 2. Bilanz & Verschuldung
    st.markdown("### 2. Bilanz & Verschuldung (Balance Sheet)")
    
    bs_years = sorted(balance_sheet.columns)
    total_assets = get_fin("Total Assets", balance_sheet)
    total_liab = get_fin("Total Liabilities Net Minority Interest", balance_sheet)
    cash = get_fin("Cash And Cash Equivalents", balance_sheet)
    st_debt = get_fin("Current Debt", balance_sheet)
    lt_debt = get_fin("Long Term Debt", balance_sheet)
    stockholders_equity = get_fin("Stockholders Equity", balance_sheet)

    total_debt = st_debt.fillna(0) + lt_debt.fillna(0)
    net_debt = total_debt - cash.fillna(0)

    bs_years_str = [pd.to_datetime(y).strftime("%Y") for y in bs_years]
    fig_bs = go.Figure()
    fig_bs.add_trace(go.Bar(x=bs_years_str, y=[total_debt.get(y, 0) / 1e9 for y in bs_years], name="Total Debt (Mrd.)", marker_color="#ef4444"))
    fig_bs.add_trace(go.Bar(x=bs_years_str, y=[cash.get(y, 0) / 1e9 for y in bs_years], name="Cash (Mrd.)", marker_color="#22c55e"))
    fig_bs.add_trace(go.Scatter(x=bs_years_str, y=[net_debt.get(y, 0) / 1e9 for y in bs_years], mode='lines+markers', name="Net Debt (Mrd.)", line=dict(color="#f97316", width=3)))
    fig_bs.update_layout(title="Liquidität vs. Gesamt- und Nettoverschuldung", margin=dict(t=40, b=20, l=20, r=20), height=350)
    st.plotly_chart(fig_bs, use_container_width=True)

    df_bs = pd.DataFrame({
        "Total Assets (Gesamtvermögen)": total_assets,
        "Total Liabilities (Gesamtverbindlichkeiten)": total_liab,
        "Cash & Cash Equivalents (Liquide Mittel)": cash,
        "Short-Term Debt (Kurzfristige Schulden)": st_debt,
        "Long-Term Debt (Langfristige Schulden)": lt_debt,
        "Total Debt (Gesamtschulden)": total_debt,
        "Net Debt (Nettoschulden)": net_debt,
    }).T
    st.dataframe(format_df(df_bs), use_container_width=True)

    # 3. Cashflow & Free Cashflow
    st.markdown("### 3. Cashflow-Rechnung & FCF-Metriken")
    
    cf_years = sorted(cashflow.columns)
    cf_years_str = [pd.to_datetime(y).strftime("%Y") for y in cf_years]
    ocf = get_fin("Operating Cash Flow", cashflow)
    capex = get_fin("Capital Expenditure", cashflow)
    fcf = ocf.fillna(0) + capex.fillna(0)

    fig_cf = go.Figure()
    fig_cf.add_trace(go.Bar(x=cf_years_str, y=[ocf.get(y, 0) / 1e9 for y in cf_years], name="Operating Cashflow (Mrd.)", marker_color="#3b82f6"))
    fig_cf.add_trace(go.Bar(x=cf_years_str, y=[abs(capex.get(y, 0)) / 1e9 for y in cf_years], name="CapEx (Mrd.)", marker_color="#f43f5e"))
    fig_cf.add_trace(go.Bar(x=cf_years_str, y=[fcf.get(y, 0) / 1e9 for y in cf_years], name="Free Cash Flow (Mrd.)", marker_color="#10b981"))
    fig_cf.update_layout(barmode='group', title="Cashflow-Komponenten & Free Cash Flow (in Mrd.)", margin=dict(t=40, b=20, l=20, r=20), height=350)
    st.plotly_chart(fig_cf, use_container_width=True)

    df_cf = pd.DataFrame({
        "Operating Cash Flow": ocf,
        "Capital Expenditures (CapEx)": capex,
        "Free Cash Flow (FCF)": fcf,
    }).T
    st.dataframe(format_df(df_cf), use_container_width=True)

    # 4. Bewertung & Marktdaten
    st.markdown("### 4. Bewertung & Marktdaten (Valuation)")
    market_cap = info.get("marketCap", np.nan)
    shares_out = info.get("sharesOutstanding")
    latest_fcf = fcf.iloc[-1] if not fcf.empty else np.nan
    p_fcf = (market_cap / latest_fcf) if (pd.notnull(market_cap) and pd.notnull(latest_fcf) and latest_fcf > 0) else "N/A"

    val_data = {
        "Kennzahl": [
            "Market Capitalization (Marktkapitalisierung)",
            "Trailing P/E (KGV)",
            "Forward P/E (Erwartetes KGV)",
            "P/FCF Ratio (Kurs-FCF-Verhältnis LTM)",
            "EV / EBITDA",
            "Shares Outstanding (Ausstehende Aktien)",
            "EPS Trailing (Gewinn je Aktie)",
            "EPS Forward"
        ],
        "Wert": [
            f"{market_cap:,.0f} {info.get('currency', '')}" if pd.notnull(market_cap) else "N/A",
            f"{info.get('trailingPE', 0):.2f}" if info.get('trailingPE') else "N/A",
            f"{info.get('forwardPE', 0):.2f}" if info.get('forwardPE') else "N/A",
            f"{p_fcf:.2f}" if isinstance(p_fcf, (int, float)) else "N/A",
            f"{info.get('enterpriseToEbitda', 0):.2f}" if info.get('enterpriseToEbitda') else "N/A",
            f"{shares_out:,.0f}" if shares_out else "N/A",
            f"{info.get('trailingEps', 0):.2f}" if info.get('trailingEps') else "N/A",
            f"{info.get('forwardEps', 0):.2f}" if info.get('forwardEps') else "N/A"
        ]
    }
    st.dataframe(pd.DataFrame(val_data), use_container_width=True)

    # 5. Dividendenhistorie
    st.markdown("### 5. Dividendenhistorie")
    if not dividends.empty:
        annual_div = dividends.resample('YE').sum()
        div_years = [d.strftime("%Y") for d in annual_div.index[-10:]]
        div_vals = annual_div.values[-10:]
        
        fig_div = go.Figure()
        fig_div.add_trace(go.Bar(x=div_years, y=div_vals, marker_color="#8b5cf6", name="Dividende je Aktie"))
        fig_div.update_layout(title="Ausschüttung je Aktie p.a. (letzte 10 Jahre)", margin=dict(t=40, b=20, l=20, r=20), height=300)
        st.plotly_chart(fig_div, use_container_width=True)
    else:
        st.info("Keine Dividendenhistorie für dieses Wertpapier vorhanden.")

    # 6. DCF Inputs & Analysten
    st.markdown("### 6. DCF-Parameter & Konsensschätzungen")
    col_dcf1, col_dcf2 = st.columns(2)
    with col_dcf1:
        target_mean = info.get("targetMeanPrice")
        rec = info.get("recommendationKey", "N/A")
        st.dataframe(pd.DataFrame({
            "Metrik": ["Empfehlung", "Kursziel Ø", "Kursziel Max", "Kursziel Min", "Analystenanzahl"],
            "Wert": [
                rec.upper(),
                f"{target_mean:,.2f}" if target_mean else "N/A",
                f"{info.get('targetHighPrice', 0):,.2f}" if info.get('targetHighPrice') else "N/A",
                f"{info.get('targetLowPrice', 0):,.2f}" if info.get('targetLowPrice') else "N/A",
                str(info.get("numberOfAnalystOpinions", "N/A"))
            ]
        }), use_container_width=True)
    
    with col_dcf2:
        beta = info.get("beta", 1.0) or 1.0
        rf = 4.25
        erp = 5.0
        cost_eq = rf + (beta * erp)
        st.dataframe(pd.DataFrame({
            "DCF Benchmark": ["Beta", "Risk-Free Rate (Rf)", "Equity Risk Premium (ERP)", "Cost of Equity (CAPM)", "Terminal Growth Target"],
            "Wert": [f"{beta:.2f}", f"{rf:.2f}%", f"{erp:.2f}%", f"{cost_eq:.2f}%", "2.0% - 2.5%"]
        }), use_container_width=True)
