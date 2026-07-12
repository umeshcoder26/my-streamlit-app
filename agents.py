from crewai import Agent
from crewai_tools import SerperDevTool
from tools.stock_fetcher import fetch_nse_stocks
from tools.technical import technical_analysis

web_search = SerperDevTool()  # Uses SERPER_API_KEY from .env

def create_stock_scout(llm):
    return Agent(
        role="Stock Scout",
        goal=(
            "Discover the most promising NSE/BSE-listed stocks for swing trading "
            "over 5–10 day holding periods. Focus on stocks with strong momentum, "
            "volume activity, and potential for 5–15% gains."
        ),
        backstory=(
            "You are a seasoned market scout who monitors Indian equity markets daily. "
            "You use real-time data feeds and market news to identify stocks showing "
            "unusual momentum, breakout patterns, or strong fundamentals entering a "
            "technically favorable zone."
        ),
        tools=[fetch_nse_stocks, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_analyst(llm):
    return Agent(
        role="Equity Analyst",
        goal=(
            "Perform deep fundamental and technical analysis on shortlisted stocks. "
            "Evaluate RSI, MACD, Bollinger Bands, P/E ratio, EPS, sector trends, "
            "and recent news to form a complete trading thesis for each stock."
        ),
        backstory=(
            "You are a CFA-level analyst with 15 years of experience in Indian equities. "
            "You combine quantitative technical signals with qualitative fundamental "
            "assessment to build high-conviction swing trade theses. You never guess — "
            "you call the tools to get real data."
        ),
        tools=[technical_analysis, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_strategist(llm):
    return Agent(
        role="Trade Strategist",
        goal=(
            "Synthesize all research into a clean, actionable swing trade plan. "
            "Produce a ranked table of the top 5 stocks with precise entry price, "
            "target price, stop loss, expected hold time, and clear reasoning."
        ),
        backstory=(
            "You are a portfolio manager who turns analyst reports into executable "
            "trade plans. You are disciplined about risk management — every trade "
            "recommendation must include a stop loss. You present findings in a "
            "structured markdown table that traders can act on immediately."
        ),
        tools=[web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )