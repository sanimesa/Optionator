import streamlit as st

st.set_page_config(
    page_title="Optionator Dashboard",
    page_icon="📈",
    layout="wide"
)

st.write("# Welcome to Optionator! 📈")

st.sidebar.success("Select a tool above.")

st.markdown(
    """
    This dashboard combines multiple tools for options analysis:

    ### 👈 Select a tool from the sidebar:

    - **Pricing (Black-Scholes):** 
        - Calculate theoretical option prices.
        - Visualize Greeks (Delta, Gamma, Theta, Vega).
        - Analyze P&L scenarios.

    - **GEX Dashboard:**
        - Visualize Gamma Exposure (GEX) profiles.
        - Analyze Open Interest (OI) distribution.
        - Load data from your local option chains.

    ---
    *Powered by OpenClaw & Streamlit*
    """
)
