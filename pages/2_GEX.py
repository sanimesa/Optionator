import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import duckdb
import json

# Set layout
st.set_page_config(layout="wide", page_title="GEX Stream Dashboard")

import os
# Adjust DB_FILE path relative to this script
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "options.db")

# --- Data Loading ---
def get_tickers():
    con = duckdb.connect(DB_FILE, read_only=True)
    df = con.execute("SELECT DISTINCT ticker FROM option_chains ORDER BY ticker").df()
    con.close()
    return df['ticker'].tolist()

def get_expiries(ticker):
    con = duckdb.connect(DB_FILE, read_only=True)
    # Filter for expiries that are today or in the future
    df = con.execute("SELECT DISTINCT expiry FROM option_chains WHERE ticker = ? AND expiry >= CURRENT_DATE ORDER BY expiry", [ticker]).df()
    con.close()
    return df['expiry'].tolist()

def get_run_dates(ticker, expiry):
    con = duckdb.connect(DB_FILE, read_only=True)
    df = con.execute("SELECT run_date FROM option_chains WHERE ticker = ? AND expiry = ? ORDER BY run_date DESC", [ticker, expiry]).df()
    con.close()
    return df['run_date'].tolist()

def load_data(ticker, expiry, run_date):
    con = duckdb.connect(DB_FILE, read_only=True)
    # Cast to string for query comparison just to be safe or use parameters carefully
    # run_date in DB is TIMESTAMP, select return datetime64[ns]
    
    # We query by parts to avoid timestamp format mismatch issues if possible
    result = con.execute("""
        SELECT raw_json FROM option_chains 
        WHERE ticker = ? AND expiry = ? AND run_date = ?
    """, [ticker, expiry, run_date]).fetchone()
    con.close()
    
    if result:
        return json.loads(result[0])
    return None

def process_chain(data):
    response = data.get('OptionChainResponse', {})
    spot_price = response.get('nearPrice', 0)
    pairs = response.get('OptionPair', [])
    
    gex_data = []
    
    for pair in pairs:
        call = pair.get('Call', {})
        put = pair.get('Put', {})
        
        strike = call.get('strikePrice', 0)
        
        # Calls
        call_oi = call.get('openInterest', 0)
        call_vol = call.get('volume', 0)
        call_gamma = 0
        if 'OptionGreeks' in call:
            call_gamma = call.get('OptionGreeks', {}).get('gamma', 0)
            
        # Puts
        put_oi = put.get('openInterest', 0)
        put_vol = put.get('volume', 0)
        put_gamma = 0
        if 'OptionGreeks' in put:
            put_gamma = put.get('OptionGreeks', {}).get('gamma', 0)
            
        # GEX Calculation
        # Call GEX = Gamma * OI * 100 * Spot
        # Put GEX = Gamma * OI * 100 * Spot * -1
        
        call_gex = call_gamma * call_oi * 100 * spot_price
        put_gex = put_gamma * put_oi * 100 * spot_price * -1
        net_gex = call_gex + put_gex
        
        gex_data.append({
            "Strike": strike,
            "Net GEX": net_gex,
            "Call OI": call_oi,
            "Put OI": put_oi,
            "Call Vol": call_vol,
            "Put Vol": put_vol,
            "Call GEX": call_gex,
            "Put GEX": put_gex
        })
        
    df = pd.DataFrame(gex_data)
    df.sort_values("Strike", inplace=True)
    return df, spot_price

# --- Charts ---

def plot_gamma_exposure(df, spot_price):
    fig = go.Figure()
    
    colors = ['#00C805' if v >= 0 else '#FF0000' for v in df['Net GEX']]
    
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Net GEX'],
        orientation='h',
        marker_color=colors,
        name='Net GEX'
    ))
    
    fig.add_hline(y=spot_price, line_dash="dash", line_color="yellow", annotation_text=f"{spot_price:.2f}")
    
    fig.update_layout(
        title="Gamma Exposure ($)",
        xaxis_title="Net GEX ($)",
        yaxis_title="Strike",
        template="plotly_dark",
        height=700,
        bargap=0.1
    )
    return fig

def plot_options_inventory(df, spot_price):
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=df['Call OI'],
        orientation='h',
        name='Call OI',
        marker_color='#00C805'
    ))
    
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=-df['Put OI'], 
        orientation='h',
        name='Put OI',
        marker_color='#FF0000',
        customdata=df['Put OI'],
        hovertemplate='%{customdata}'
    ))
    
    fig.add_hline(y=spot_price, line_dash="dash", line_color="yellow", annotation_text=f"{spot_price:.2f}")
    
    fig.update_layout(
        title="Options Inventory (OI)",
        xaxis_title="Contracts",
        yaxis_title="Strike",
        template="plotly_dark",
        height=700,
        bargap=0.1,
        barmode='overlay' 
    )
    return fig

# --- Main App ---

def main():
    st.title("GEX Stream Dashboard")
    
    # Sidebar
    st.sidebar.header("Configuration")
    
    try:
        tickers = get_tickers()
    except Exception as e:
        st.error(f"DB Error: {e}")
        return

    if not tickers:
        st.warning("No data in options.db. Run ingest_options.py first.")
        return

    ticker = st.sidebar.selectbox("Ticker", tickers)
    
    expiries = get_expiries(ticker)
    expiry = st.sidebar.selectbox("Expiry", expiries)
    
    run_dates = get_run_dates(ticker, expiry)
    run_date = st.sidebar.selectbox("Run Date", run_dates)
    
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Load and Process
    raw_json = load_data(ticker, expiry, run_date)
    
    if raw_json:
        df, spot = process_chain(raw_json)
        
        # Summary Metrics
        total_gex = df['Net GEX'].sum()
        total_call_gex = df['Call GEX'].sum()
        total_put_gex = df['Put GEX'].sum()
        total_call_vol = df['Call Vol'].sum()
        total_put_vol = df['Put Vol'].sum()
        
        # Find Largest GEX Strikes
        max_call_row = df.loc[df['Call GEX'].idxmax()]
        max_put_row = df.loc[df['Put GEX'].idxmin()] # Put GEX is negative
        
        st.markdown(f"### {ticker} (Spot: ${spot:.2f})")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net GEX", f"${total_gex/1e6:.2f}M")
        m2.metric("Call GEX", f"${total_call_gex/1e6:.2f}M")
        m3.metric("Put GEX", f"${total_put_gex/1e6:.2f}M")
        m4.metric("GEX Ratio (C/P)", f"{abs(total_call_gex/total_put_gex):.2f}" if total_put_gex != 0 else "N/A")

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Expiry", str(expiry))
        m6.metric("Call Volume", f"{int(total_call_vol):,}")
        m7.metric("Put Volume", f"{int(total_put_vol):,}")
        m8.metric("P/C Vol Ratio", f"{total_put_vol/total_call_vol:.2f}" if total_call_vol != 0 else "N/A")

        st.divider()

        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(plot_gamma_exposure(df, spot), use_container_width=True)
        with c2:
            st.plotly_chart(plot_options_inventory(df, spot), use_container_width=True)
            
        # Detail Table
        with st.expander("Raw Data"):
            st.dataframe(df.style.format({
                "Net GEX": "${:,.0f}",
                "Call GEX": "${:,.0f}",
                "Put GEX": "${:,.0f}",
                "Strike": "{:.1f}"
            }))
            
    else:
        st.error("Failed to load data.")

if __name__ == "__main__":
    main()
