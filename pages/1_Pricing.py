import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm

st.set_page_config(page_title="Optionator", page_icon="📈", layout="wide")

st.title("📈 Optionator: Options Strategy Analyzer")
st.markdown("Visualize option payoffs and Greeks.")

# --- Sidebar Inputs ---
st.sidebar.header("Option Parameters")

spot_price = st.sidebar.number_input("Stock Price (S)", value=100.0)
strike_price = st.sidebar.number_input("Strike Price (K)", value=100.0)
time_to_expiry = st.sidebar.number_input("Days to Expiry (T)", value=30.0) / 365.0
volatility = st.sidebar.slider("Implied Volatility (σ)", 0.0, 2.0, 0.2, 0.01)
risk_free_rate = st.sidebar.number_input("Risk-Free Rate (r)", value=0.05)
option_type = st.sidebar.radio("Option Type", ["Call", "Put"])

# --- Black-Scholes Model ---
def black_scholes(S, K, T, r, sigma, type="Call"):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if type == "Call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = -norm.cdf(-d1)
        
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    theta = -(S * sigma * norm.pdf(d1)) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2 if type == "Call" else -d2)
    vega = S * np.sqrt(T) * norm.pdf(d1)
    
    return price, delta, gamma, theta / 365, vega / 100

price, delta, gamma, theta, vega = black_scholes(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility, option_type)

# --- Display Greeks ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Option Price", f"${price:.2f}")
col2.metric("Delta (Δ)", f"{delta:.3f}")
col3.metric("Gamma (Γ)", f"{gamma:.4f}")
col4.metric("Theta (Θ)", f"{theta:.3f}/day")
col5.metric("Vega (ν)", f"{vega:.3f}/1%")

# --- Payoff Diagram ---
st.subheader("Payoff Diagram (At Expiry)")
prices = np.linspace(spot_price * 0.5, spot_price * 1.5, 100)
payoffs = []

for p in prices:
    intrinsic_value = max(0, p - strike_price) if option_type == "Call" else max(0, strike_price - p)
    # Simple payoff calculation assuming long position
    payoffs.append(intrinsic_value - price)

fig = go.Figure()
fig.add_trace(go.Scatter(x=prices, y=payoffs, mode='lines', name='P&L'))
fig.add_vline(x=spot_price, line_dash="dash", line_color="gray", annotation_text="Current Price")
fig.add_hline(y=0, line_color="black", line_width=1)
fig.update_layout(title=f"Long {option_type} P&L", xaxis_title="Stock Price at Expiry", yaxis_title="Profit / Loss ($)")

st.plotly_chart(fig, use_container_width=True)

# --- Explanation ---
with st.expander("Greeks Explanation"):
    st.markdown("""
    - **Delta (Δ):** Rate of change of option price with respect to the underlying asset's price.
    - **Gamma (Γ):** Rate of change of Delta with respect to the underlying asset's price.
    - **Theta (Θ):** Rate of change of option price with respect to time (Time Decay).
    - **Vega (ν):** Rate of change of option price with respect to volatility.
    """)
