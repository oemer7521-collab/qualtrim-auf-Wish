import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="Financial Metrics Dashboard", layout="wide")

st.title("📊 Financial Metrics & Valuation Explorer")
st.caption("Umfassende Fundamentalanalyse, Bilanzdaten, Bewertung & DCF-Metriken")

# Ticker-Suche über Name oder Symbol
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

    # Formatierungshelfer für Tabellen
    def format_df(df: pd.DataFrame) -> pd.DataFrame:
        formatted = df.copy()
        formatted.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") if isinstance(c, (pd.Timestamp, str)) else str(c) for c in formatted.columns]
        for col in formatted.columns:
            formatted[col] = formatted[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else ("N/A" if pd.isna(x) else x))
        return formatted

    # TAB 1: GuV / Income Statement & Margen
    st.markdown("### 1. Gewinn- und Verlustrechnung (Income Statement) & Margen")
    
    inc_rows = {}
    years = financials.columns

    def get_fin(key, df):
        return df.loc[key] if key in df.index else pd.Series(index=years, dtype=float)

    rev = get_fin("Total Revenue", financials)
    gross_profit = get_fin("Gross Profit", financials)
    ebit = get_fin("Operating Income", financials)
    net_income = get_fin("Net Income", financials)
    ebitda = get_fin("EBITDA", financials)

    inc_rows["Revenue (Umsatz)"] = rev
    inc_rows["Gross Profit (Bruttogewinn)"] = gross_profit
    inc_rows["Operating Income / EBIT"] = ebit
    inc_rows["EBITDA"] = ebitda
    inc_rows["Net Income (Nettogewinn)"] = net_income

    df_inc = pd.DataFrame(inc_rows).T

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
        st.write("**Absolute Zahlen (in Währung)**")
        st.dataframe(format_df(df_inc), use_container_width=True)
    with col_is2:
        st.write("**Margenprofil**")
        disp_margins = margins.map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
        disp_margins.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in disp_margins.columns]
        st.dataframe(disp_margins, use_container_width=True)

    # TAB 2: Bilanz & Verschuldung
    st.markdown("### 2. Bilanz & Verschuldung (Balance Sheet)")
    
    bs_years = balance_sheet.columns
    total_assets = get_fin("Total Assets", balance_sheet)
    total_liab = get_fin("Total Liabilities Net Minority Interest", balance_sheet)
    cash = get_fin("Cash And Cash Equivalents", balance_sheet)
    st_debt = get_fin("Current Debt", balance_sheet)
    lt_debt = get_fin("Long Term Debt", balance_sheet)
    stockholders_equity = get_fin("Stockholders Equity", balance_sheet)

    total_debt = st_debt.fillna(0) + lt_debt.fillna(0)
    net_debt = total_debt - cash.fillna(0)

    bs_dict = {
        "Total Assets (Gesamtvermögen)": total_assets,
        "Total Liabilities (Gesamtverbindlichkeiten)": total_liab,
        "Cash & Cash Equivalents (Liquide Mittel)": cash,
        "Short-Term Debt (Kurzfristige Schulden)": st_debt,
        "Long-Term Debt (Langfristige Schulden)": lt_debt,
        "Total Debt (Gesamtschulden)": total_debt,
        "Net Debt (Nettoschulden)": net_debt,
    }
    df_bs = pd.DataFrame(bs_dict).T

    ratios_bs = pd.DataFrame(index=["Debt-to-Equity Ratio", "Net Debt / EBITDA"], columns=bs_years)
    for y in bs_years:
        eq = stockholders_equity.get(y, np.nan)
        eb = ebitda.get(y, np.nan) if y in ebitda else np.nan
        nd = net_debt.get(y, np.nan)
        td = total_debt.get(y, np.nan)
        
        ratios_bs.loc["Debt-to-Equity Ratio", y] = (td / eq) if pd.notnull(eq) and eq != 0 else np.nan
        ratios_bs.loc["Net Debt / EBITDA", y] = (nd / eb) if pd.notnull(eb) and eb != 0 else np.nan

    col_bs1, col_bs2 = st.columns(2)
    with col_bs1:
        st.dataframe(format_df(df_bs), use_container_width=True)
    with col_bs2:
        st.write("**Verschuldungskennzahlen**")
        disp_ratios_bs = ratios_bs.map(lambda x: f"{x:.2f}x" if pd.notnull(x) else "N/A")
        disp_ratios_bs.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in disp_ratios_bs.columns]
        st.dataframe(disp_ratios_bs, use_container_width=True)

    # TAB 3: Cashflow & Free Cashflow
    st.markdown("### 3. Cashflow-Rechnung & FCF-Metriken")
    
    cf_years = cashflow.columns
    ocf = get_fin("Operating Cash Flow", cashflow)
    capex = get_fin("Capital Expenditure", cashflow)
    fcf = ocf.fillna(0) + capex.fillna(0)

    market_cap = info.get("marketCap", np.nan)

    cf_dict = {
        "Operating Cash Flow": ocf,
        "Capital Expenditures (CapEx)": capex,
        "Free Cash Flow (FCF)": fcf,
    }
    df_cf = pd.DataFrame(cf_dict).T

    fcf_yield_row = pd.DataFrame(index=["FCF Yield (%)"], columns=cf_years)
    for y in cf_years:
        curr_fcf = fcf.get(y, np.nan)
        if pd.notnull(curr_fcf) and pd.notnull(market_cap) and market_cap > 0:
            fcf_yield_row.loc["FCF Yield (%)", y] = (curr_fcf / market_cap) * 100

    col_cf1, col_cf2 = st.columns(2)
    with col_cf1:
        st.dataframe(format_df(df_cf), use_container_width=True)
    with col_cf2:
        st.write("**Free Cashflow Rendite (auf Basis aktueller Marktkapitalisierung)**")
        disp_fcf_yield = fcf_yield_row.map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
        disp_fcf_yield.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in disp_fcf_yield.columns]
        st.dataframe(disp_fcf_yield, use_container_width=True)

    # TAB 4: Bewertung & Marktdaten (Valuation)
    st.markdown("### 4. Bewertung & Marktdaten (Valuation)")
    
    shares_out = info.get("sharesOutstanding")
    latest_fcf = fcf.iloc[0] if not fcf.empty else np.nan
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

    # TAB 5: Dividenden
    st.markdown("### 5. Dividenden")
    
    div_yield = info.get("dividendYield")
    payout_ratio = info.get("payoutRatio")
    
    div_growth = {}
    if not dividends.empty:
        annual_div = dividends.resample('YE').sum()
        for period, label in [(1, "1 Jahr"), (3, "3 Jahre"), (5, "5 Jahre"), (10, "10 Jahre")]:
            if len(annual_div) > period:
                start = annual_div.iloc[-period - 1]
                end = annual_div.iloc[-1]
                if start > 0 and end > 0:
                    cagr = ((end / start) ** (1 / period) - 1) * 100
                    div_growth[f"Wachstumsrate ({label} CAGR)"] = f"{cagr:.2f}%"
                else:
                    div_growth[f"Wachstumsrate ({label} CAGR)"] = "N/A"
            else:
                div_growth[f"Wachstumsrate ({label} CAGR)"] = "Keine Daten"

    col_div1, col_div2 = st.columns(2)
    with col_div1:
        st.write("**Aktuelle Renditen & Quoten**")
        df_div_base = pd.DataFrame({
            "Metrik": ["Dividend Yield (Dividendenrendite)", "Payout Ratio (nach Gewinn)", "Dividend Rate (Aktuell p.a.)"],
            "Wert": [
                f"{div_yield * 100:.2f}%" if div_yield else "0.00%",
                f"{payout_ratio * 100:.2f}%" if payout_ratio else "N/A",
                f"{info.get('dividendRate', 0):.2f} {info.get('currency', '')}" if info.get('dividendRate') else "0.00"
            ]
        })
        st.dataframe(df_div_base, use_container_width=True)

    with col_div2:
        st.write("**Historisches Dividendenwachstum (CAGR)**")
        if div_growth:
            st.dataframe(pd.DataFrame(list(div_growth.items()), columns=["Zeitraum", "CAGR"]), use_container_width=True)
        else:
            st.info("Keine ausreichende Dividendenausschüttung in der Historie.")

    # TAB 6: Prognosen, Analysten & DCF-Inputs
    st.markdown("### 6. Analyst Estimates, Beat/Miss & DCF Inputs")
    
    col_est1, col_est2 = st.columns(2)
    
    with col_est1:
        st.write("**Analyst Estimates (Konsensschätzungen)**")
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        rec = info.get("recommendationKey", "N/A")

        df_analysts = pd.DataFrame({
            "Metrik": ["Empfehlung (Konsens)", "Kursziel Mittelwert", "Kursziel Hoch", "Kursziel Tief", "Anzahl Analysten"],
            "Wert": [
                rec.upper(),
                f"{target_mean:,.2f}" if target_mean else "N/A",
                f"{target_high:,.2f}" if target_high else "N/A",
                f"{target_low:,.2f}" if target_low else "N/A",
                str(info.get("numberOfAnalystOpinions", "N/A"))
            ]
        })
        st.dataframe(df_analysts, use_container_width=True)

    with col_est2:
        st.write("**DCF Inputs & Modellparameter (Standardannahmen)**")
        beta = info.get("beta", 1.0) or 1.0
        rf_rate = 4.25
        erp = 5.0
        cost_of_equity = rf_rate + (beta * erp)

        df_dcf = pd.DataFrame({
            "DCF Parameter": [
                "Beta (Aktie)",
                "Risk-Free Rate (Rf)",
                "Equity Risk Premium (ERP)",
                "Estimated Cost of Equity (CAPM)",
                "Empfohlene Terminal Growth Rate"
            ],
            "Wert": [
                f"{beta:.2f}",
                f"{rf_rate:.2f}%",
                f"{erp:.2f}%",
                f"{cost_of_equity:.2f}%",
                "2.00% - 2.50%"
            ]
        })
        st.dataframe(df_dcf, use_container_width=True)
