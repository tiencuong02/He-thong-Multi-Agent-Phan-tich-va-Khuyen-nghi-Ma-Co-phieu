from crewai import Agent
from app.agents.tools import fetch_stock_data, fetch_news

def create_market_researcher() -> Agent:
    return Agent(
        role='Market Researcher',
        goal='Gather comprehensive historical price data, volume, and the latest news for a given stock ticker.',
        backstory='You are an expert market researcher. You excel at finding the most up-to-date and relevant financial data and news articles for any given company.',
        verbose=True,
        allow_delegation=False,
        tools=[fetch_stock_data, fetch_news]
    )
