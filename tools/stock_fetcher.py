import os
import time
import requests
from dotenv import load_dotenv
from crewai.tools import tool

load_dotenv()
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# Free tier is rate-limited (5 calls/min, 25 calls/day as of 2025+).
# We sleep between calls to stay under the per-minute limit.
_ALPHA_VANTAGE_DELAY_SECONDS = 13

# Broader curated fallback (Nifty 100-ish) used only if live sources fail.
FALLBACK_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "LT.NS",
    "ITC.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS",
    "SUNPHARMA.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TECHM.NS", "POWERGRID.NS",
    "NTPC.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "BAJAJFINSV.NS",
    "BPCL.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS",
    "HINDALCO.NS", "INDUSINDBK.NS", "JSWSTEEL.NS", "M&M.NS", "NESTLEIND.NS",
    "ONGC.NS", "SBILIFE.NS", "SHREECEM.NS", "TATACONSUM.NS", "TATAMOTORS.NS",
    "TATASTEEL.NS", "UPL.NS", "BAJAJ-AUTO.NS", "BRITANNIA.NS", "APOLLOHOSP.NS",
]


def _to_alpha_vantage_symbol(ticker: str) -> str:
    """Convert a yfinance-style NSE ticker (RELIANCE.NS) to Alpha Vantage's
    NSE-prefixed format (NSE:RELIANCE), which is how Alpha Vantage identifies
    Indian NSE-listed equities."""
    base = ticker.replace(".NS", "").replace(".BO", "")
    return f"NSE:{base}"


def _fetch_alpha_vantage_daily(ticker: str) -> dict | None:
    """Fetch daily OHLCV history for a ticker from Alpha Vantage.
    Returns a dict of {date: {close, volume}} sorted ascending by date, or None on failure."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("ALPHA_VANTAGE_API_KEY not set in .env.")
        return None

    symbol = _to_alpha_vantage_symbol(ticker)
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact",  # last ~100 trading days
        "apikey": api_key,
    }

    try:
        resp = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)
        data = resp.json()
    except Exception as e:
        print(f"Alpha Vantage request failed for {symbol}: {e}")
        return None

    if "Note" in data:
        print(f"Alpha Vantage rate limit hit: {data['Note']}")
        return None
    if "Information" in data:
        print(f"Alpha Vantage limit/info message: {data['Information']}")
        return None
    if "Error Message" in data:
        print(f"Alpha Vantage error for {symbol}: {data['Error Message']}")
        return None

    series = data.get("Time Series (Daily)")
    if not series:
        print(f"No Alpha Vantage data returned for {symbol}.")
        return None

    parsed = {}
    for date_str, values in series.items():
        try:
            parsed[date_str] = {
                "close": float(values["4. close"]),
                "volume": float(values["5. volume"]),
            }
        except (KeyError, ValueError):
            continue

    return dict(sorted(parsed.items()))  # ascending by date


def fetch_tickers_live(count: int = 20) -> list:
    """Fetches most active NSE stocks via nsepython, with curated fallback.
    (Ticker discovery stays separate from Alpha Vantage, which has no free
    India-market screener endpoint.)"""
    try:
        from nsepython import nse_most_active
        df = nse_most_active()
        if df is not None and not df.empty:
            symbols = df["symbol"].astype(str).str.strip().str.upper().tolist()
            tickers = [f"{s}.NS" for s in symbols if s]
            if tickers:
                return tickers[:count]
    except ImportError:
        print("nsepython not installed. Run: pip install nsepython")
    except Exception as e:
        print(f"nsepython fetch failed: {e}")

    print("Live NSE source unavailable. Using curated fallback list.")
    return FALLBACK_TICKERS[:count]


@tool("fetch_nse_stocks")
def fetch_nse_stocks(num_stocks: int = 5) -> str:
    """
    Fetches most active NSE stocks, then ranks them by momentum and volume
    using delayed daily data from Alpha Vantage. Returns top swing trade candidates.

    Note: Alpha Vantage's free tier is capped at 25 requests/day and 5/minute,
    so only a small number of tickers can be scanned per run.
    """
    # Alpha Vantage free tier is very rate-limited, so we only scan a small
    # pool rather than a wide one.
    max_scan = min(8, max(num_stocks * 2, num_stocks))
    tickers = fetch_tickers_live(count=max_scan)

    candidates = []
    for i, ticker in enumerate(tickers):
        if i > 0:
            time.sleep(_ALPHA_VANTAGE_DELAY_SECONDS)  # respect Alpha Vantage rate limit

        history = _fetch_alpha_vantage_daily(ticker)
        if not history or len(history) < 20:
            continue

        try:
            dates = list(history.keys())
            closes = [history[d]["close"] for d in dates]
            volumes = [history[d]["volume"] for d in dates]

            latest_close = closes[-1]
            prev_close_5d = closes[-6]
            ma20 = sum(closes[-20:]) / 20
            vol_avg_10d = sum(volumes[-10:]) / 10

            momentum_5d = (latest_close - prev_close_5d) / prev_close_5d * 100
            vol_spike = volumes[-1] / vol_avg_10d if vol_avg_10d else 0
            above_ma20 = latest_close > ma20
            score = momentum_5d + (vol_spike * 2)

            candidates.append({
                "ticker": ticker,
                "price": round(latest_close, 2),
                "momentum_5d_pct": round(momentum_5d, 2),
                "vol_spike": round(vol_spike, 2),
                "above_ma20": above_ma20,
                "score": round(score, 2),
            })
        except (IndexError, ZeroDivisionError):
            continue

    top = sorted(candidates, key=lambda x: x["score"], reverse=True)[:num_stocks]

    output = f"## Top {num_stocks} NSE Stocks by Momentum + Volume (Alpha Vantage, Delayed)\n\n"
    if not top:
        output += "- No valid candidates found (check ALPHA_VANTAGE_API_KEY and daily rate limit).\n"
    for r in top:
        output += (
            f"**{r['ticker']}** | Price: ₹{r['price']} | "
            f"5D Momentum: {r['momentum_5d_pct']}% | "
            f"Volume Spike: {r['vol_spike']}x | "
            f"Above MA20: {r['above_ma20']} | Score: {r['score']}\n\n"
        )
    return output