from crewai import Agent
from app.agents.tools import fetch_fundamentals, analyze_sentiment

def create_financial_analyst() -> Agent:
    return Agent(
        role='Financial Analyst',
        goal='Analyze financial fundamentals and compute sentiment scores from news articles to assess the financial health and market perception of a company.',
        backstory='You are a seasoned financial analyst. You can read between the lines of news articles to gauge market sentiment and you have a deep understanding of financial metrics like PE ratio, EPS, and market cap.',
        verbose=True,
        allow_delegation=False,
        tools=[fetch_fundamentals, analyze_sentiment]
    )
