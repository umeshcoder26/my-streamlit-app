import os
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf


load_dotenv()

from tools.stock_fetcher import fetch_tickers_live

def _resolve_llm_config() -> dict:
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if provider in {"gemini", "google"}:
        if not gemini_key:
            raise RuntimeError("LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not configured.")
        return {"provider": "gemini", "model": "gemini-2.0-flash", "api_key": gemini_key}

    if provider in {"openai", "gpt"}:
        if not openai_key:
            raise RuntimeError("LLM_PROVIDER is set to 'openai' but OPENAI_API_KEY is not configured.")
        return {"provider": "openai", "model": "gpt-4o-mini", "api_key": openai_key}

    if provider in {"openrouter", "router"}:
        if not openrouter_key:
            raise RuntimeError("LLM_PROVIDER is set to 'openrouter' but OPENROUTER_API_KEY is not configured.")
        return {
            "provider": "openrouter",
            "model": "openrouter/openai/gpt-4o-mini",
            "api_key": openrouter_key,
            "base_url": "https://openrouter.ai/api/v1",
        }

    if openrouter_key:
        return {
            "provider": "openrouter",
            "model": "openrouter/openai/gpt-4o-mini",
            "api_key": openrouter_key,
            "base_url": "https://openrouter.ai/api/v1",
        }

    if gemini_key:
        return {"provider": "gemini", "model": "gemini-2.0-flash", "api_key": gemini_key}

    if openai_key:
        return {"provider": "openai", "model": "gpt-4o-mini", "api_key": openai_key}

    raise RuntimeError(
        "No supported LLM API key found. Set GEMINI_API_KEY, OPENAI_API_KEY, or OPENROUTER_API_KEY (optionally LLM_PROVIDER)."
    )


def _build_fallback_report(market="NSE", num_stocks=5, error_message=None) -> str:
    tickers = fetch_tickers_live(count=max(5, num_stocks))
    candidates = []

    for ticker in tickers[:max(5, num_stocks)]:
        try:
            hist = yf.Ticker(ticker).history(period="1mo")
            if hist.empty or len(hist) < 10:
                continue

            close = hist["Close"].dropna()
            volume = hist["Volume"].dropna()
            if close.empty or volume.empty or len(close) < 7 or len(volume) < 10:
                continue

            latest_close = close.iloc[-1]
            prev_close = close.iloc[-6]
            prev_volume_mean = volume.rolling(10).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]

            if pd.isna(latest_close) or pd.isna(prev_close) or pd.isna(prev_volume_mean) or pd.isna(ma20):
                continue

            momentum_5d = (latest_close - prev_close) / prev_close * 100
            vol_spike = volume.iloc[-1] / prev_volume_mean
            above_ma20 = latest_close > ma20
            score = momentum_5d + (vol_spike * 2)

            candidates.append(
                {
                    "ticker": ticker,
                    "price": round(latest_close, 2),
                    "momentum_5d_pct": round(momentum_5d, 2),
                    "vol_spike": round(vol_spike, 2),
                    "above_ma20": above_ma20,
                    "score": round(score, 2),
                }
            )
        except Exception:
            continue

    top = sorted(candidates, key=lambda x: x["score"], reverse=True)[:5]

    output = "## Quick Market Scan (Fallback Report)\n\n"
    if error_message:
        output += f"The AI analysis could not be completed: {error_message}\n\n"
    output += f"Here are the strongest {market} candidates from the live fallback scan:\n\n"

    if not top:
        output += "- No valid market data could be computed right now.\n"
    else:
        for row in top:
            output += (
                f"- **{row['ticker']}** | Price: ₹{row['price']} | "
                f"5D Momentum: {row['momentum_5d_pct']}% | Volume Spike: {row['vol_spike']}x | "
                f"Above MA20: {row['above_ma20']} | Score: {row['score']}\n"
            )

    output += "\n> This fallback report is shown because the CrewAI/LLM provider was unavailable or returned an API error."
    return output


def _build_llm():
    try:
        config = _resolve_llm_config()
        from crewai import LLM
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "The CrewAI LLM provider is unavailable in this environment."
        ) from exc

    try:
        llm_kwargs = {
            "model": config["model"],
            "api_key": config["api_key"],
            "temperature": 0.2,
        }
        if config.get("base_url"):
            llm_kwargs["base_url"] = config["base_url"]
        return LLM(**llm_kwargs)
    except Exception as exc:
        raise RuntimeError(
            "The LLM provider could not be initialized. Verify your API key and network access."
        ) from exc


def build_and_run_crew(market="NSE", num_stocks=15) -> str:
    try:
        from crewai import Crew, Process
        from agents import create_stock_scout, create_analyst, create_strategist
        from tasks import create_scouting_task, create_analysis_task, create_strategy_task

        llm = _build_llm()
    except Exception as exc:
        return _build_fallback_report(market=market, num_stocks=num_stocks, error_message=str(exc))

    try:
        scout = create_stock_scout(llm)
        analyst = create_analyst(llm)
        strategist = create_strategist(llm)

        task1 = create_scouting_task(scout, market=market, num_stocks=num_stocks)
        task2 = create_analysis_task(analyst, context_tasks=[task1])
        task3 = create_strategy_task(strategist, context_tasks=[task1, task2])

        crew = Crew(
            agents=[scout, analyst, strategist],
            tasks=[task1, task2, task3],
            process=Process.sequential,
            verbose=True,
        )

        return str(crew.kickoff())
    except Exception as exc:
        return _build_fallback_report(market=market, num_stocks=num_stocks, error_message=str(exc))