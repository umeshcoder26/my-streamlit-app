import yfinance as yf
import pandas as pd
import ta
from crewai.tools import tool

@tool("technical_analysis")
def technical_analysis(ticker: str) -> str:
    """
    Runs RSI, MACD, Bollinger Bands, and volume analysis on a given NSE ticker.
    Input should be the ticker symbol e.g. 'RELIANCE.NS'
    Returns technical signals to help decide buy/sell for swing trading.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")

        if hist.empty:
            return f"No data found for {ticker}"

        close = hist["Close"]
        volume = hist["Volume"]

        # RSI (14-day)
        rsi_indicator = ta.momentum.RSIIndicator(close, window=14)
        current_rsi = round(rsi_indicator.rsi().iloc[-1], 2)

        # MACD
        macd_indicator = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
        macd_val = round(macd_indicator.macd().iloc[-1], 4)
        signal_val = round(macd_indicator.macd_signal().iloc[-1], 4)
        macd_hist = round(macd_indicator.macd_diff().iloc[-1], 4)

        # Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        bb_upper = round(bb_indicator.bollinger_hband().iloc[-1], 2)
        bb_lower = round(bb_indicator.bollinger_lband().iloc[-1], 2)
        bb_mid = round(bb_indicator.bollinger_mavg().iloc[-1], 2)
        current_price = round(close.iloc[-1], 2)

        # Volume spike detection
        avg_vol = volume.rolling(20).mean().iloc[-1]
        latest_vol = volume.iloc[-1]
        vol_ratio = round(latest_vol / avg_vol, 2)

        # Simple signal generation
        rsi_signal = "Oversold (Buy Zone)" if current_rsi < 35 else ("Overbought (Caution)" if current_rsi > 70 else "Neutral")
        macd_signal = "Bullish Crossover" if macd_val > signal_val else "Bearish Crossover"
        bb_signal = "Near Lower Band (Support)" if current_price <= bb_lower * 1.02 else (
            "Near Upper Band (Resistance)" if current_price >= bb_upper * 0.98 else "Mid-Range"
        )

        return (
            f"## Technical Analysis: {ticker}\n"
            f"Current Price: ₹{current_price}\n\n"
            f"**RSI (14):** {current_rsi} → {rsi_signal}\n"
            f"**MACD:** {macd_val} | Signal: {signal_val} | Histogram: {macd_hist} → {macd_signal}\n"
            f"**Bollinger Bands:** Lower ₹{bb_lower} | Mid ₹{bb_mid} | Upper ₹{bb_upper} → {bb_signal}\n"
            f"**Volume Ratio (vs 20d avg):** {vol_ratio}x {'⚠️ Spike!' if vol_ratio > 1.5 else ''}\n"
        )
    except Exception as e:
        return f"Error analyzing {ticker}: {str(e)}"