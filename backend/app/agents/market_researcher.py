from crewai import Agent, LLM
from app.agents.tools import fetch_stock_data, fetch_news
import os

def create_market_researcher() -> Agent:
    # Use native Google provider to bypass litellm
    llm = LLM(
        model=os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash"),
        api_key=os.getenv("GOOGLE_API_KEY")
    )
    return Agent(
        role='Market Researcher',
        goal='Gather comprehensive historical price data, volume, and the latest news for a given stock ticker.',
        backstory='You are an expert market researcher. You excel at finding the most up-to-date and relevant financial data and news articles for any given company.',
        verbose=True,
        allow_delegation=False,
        tools=[fetch_stock_data, fetch_news],
        llm=llm
    )
