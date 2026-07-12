import streamlit as st
import threading
from crew import build_and_run_crew

st.set_page_config(
    page_title="NSE Swing Trader AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 NSE Swing Trading Analyst")
st.caption("Powered by CrewAI + Gemini + yFinance | Real-time multi-agent analysis")

with st.sidebar:
    st.header("⚙️ Settings")
    market = st.selectbox("Market", ["NSE", "BSE"], index=0)
    num_stocks = st.slider("Stocks to Scan", min_value=5, max_value=25, value=5)
    st.markdown("---")
    st.info(
        "**How it works:**\n"
        "1. 🔍 Scout fetches live stock data\n"
        "2. 📊 Analyst runs technical + fundamental research\n"
        "3. 🎯 Strategist outputs your trade plan"
    )

col1, col2 = st.columns([2, 1])
with col1:
    run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
with col2:
    st.caption("Takes 2–4 minutes")

if run_btn:
    st.divider()

    # Live status updates
    status = st.status("Starting multi-agent analysis...", expanded=True)

    with status:
        st.write("🔍 Agent 1 (Scout): Fetching live NSE stock data...")
        result_container = st.empty()

        try:
            with st.spinner("Agents are working in real-time..."):
                # Agent progress hints (CrewAI logs to stdout)
                result = build_and_run_crew(market=market, num_stocks=num_stocks)

            status.update(label="✅ Analysis Complete!", state="complete")

            st.subheader("📋 Swing Trade Recommendations")
            st.markdown(result)

            # Download button
            st.download_button(
                label="📥 Download Report",
                data=result,
                file_name="swing_trade_report.md",
                mime="text/markdown",
            )

        except Exception as e:
            status.update(label="❌ Error occurred", state="error")
            st.error(f"Analysis failed: {str(e)}")
            st.exception(e)