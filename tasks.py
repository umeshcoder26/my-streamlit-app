from crewai import Task

def create_scouting_task(agent, market="NSE", num_stocks=5):
    return Task(
        description=(
            f"Scan the {market} market using the fetch_nse_stocks tool. "
            f"It will return the top 5 stocks ranked by momentum and volume. "
            f"Use web search to check for any recent news or events affecting these stocks. "
            f"Return all 5 tickers with a brief reason why each is worth deeper analysis."
        ),
        expected_output=(
            "A list of 5 NSE stock tickers with their current price, key metrics, "
            "and a 1–2 sentence reason why each is worth analyzing."
        ),
        agent=agent,
    )


def create_analysis_task(agent, context_tasks):
    return Task(
        description=(
            "For each of the 5 stocks shortlisted by the Scout, run technical_analysis "
            "tool to get RSI, MACD, Bollinger Band data. Use web search to find latest "
            "news, quarterly results, or analyst upgrades/downgrades. "
            "Combine technical signals with fundamental data (P/E, EPS, sector outlook) "
            "and rank all 5 stocks from strongest to weakest swing trade potential."
        ),
        expected_output=(
            "A ranked analysis of all 5 stocks including technical signals, "
            "fundamentals, recent news, and overall swing trade potential score."
        ),
        agent=agent,
        context=context_tasks,
    )


def create_strategy_task(agent, context_tasks):
    return Task(
        description=(
            "Based on the analyst's research, pick the BEST 2–3 stocks only — "
            "the ones with the strongest confluence of technical + fundamental signals. "
            "Discard the rest. For each of your 2–3 picks, provide:\n"
            "1. Entry Price (buy zone)\n"
            "2. Target Price (upside based on resistance)\n"
            "3. Stop Loss (max 5–7% below entry)\n"
            "4. Expected Hold Time (in trading days)\n"
            "5. Risk/Reward Ratio\n"
            "6. Conviction Level (High/Medium/Low)\n"
            "7. Reason (1–2 lines)\n\n"
            "Format as a clean markdown table. "
            "Add a brief Market Context note at the top (2–3 sentences). "
            "End with a Risk Disclaimer."
        ),
        expected_output=(
            "A markdown swing trading plan with:\n"
            "- Market context paragraph\n"
            "- Table with 2–3 rows: Stock | Entry ₹ | Target ₹ | Stop Loss ₹ | "
            "Hold (Days) | R:R | Conviction | Reason\n"
            "- Risk disclaimer"
        ),
        agent=agent,
        context=context_tasks,
    )