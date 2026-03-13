from crewai import Crew, Task, Process
from pydantic import BaseModel, Field
import json
from app.agents.market_researcher import create_market_researcher
from app.agents.financial_analyst import create_financial_analyst
from app.agents.investment_advisor import create_investment_advisor

class FinalReport(BaseModel):
    ticker: str = Field(description="The stock ticker symbol being analyzed")
    risk_opportunity: str = Field(description="Detailed summary of risks and opportunities")
    recommendation: str = Field(description="The final recommendation: Buy, Hold, or Sell")

def run_analysis(ticker: str) -> dict:
    market_researcher = create_market_researcher()
    financial_analyst = create_financial_analyst()
    investment_advisor = create_investment_advisor()

    research_task = Task(
        description=f'Gather historical price data and latest news for {ticker}.',
        expected_output=f'A summary of recent price movements and key news headlines for {ticker}.',
        agent=market_researcher
    )

    analysis_task = Task(
        description=f'Analyze the fundamentals and news sentiment for {ticker} based on the gathered research.',
        expected_output=f'A detailed analysis of financial health metrics (PE, EPS) and market sentiment for {ticker}.',
        agent=financial_analyst,
        context=[research_task]
    )

    advisor_task = Task(
        description=f'Based on the research and analysis, determine whether {ticker} is a Buy, Hold, or Sell. Provide a clear rationale detailing risks and opportunities.',
        expected_output=f'A final investment recommendation for {ticker} formatted as a JSON object according to the schema.',
        agent=investment_advisor,
        context=[research_task, analysis_task],
        output_json=FinalReport
    )

    crew = Crew(
        agents=[market_researcher, financial_analyst, investment_advisor],
        tasks=[research_task, analysis_task, advisor_task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    
    # Extract the resulting object. Depending on CrewAI version, this might be a CrewOutput object.
    try:
        # If output_json was mapped, pydantic attribute exists
        if hasattr(advisor_task.output, 'json_dict') and advisor_task.output.json_dict:
             return advisor_task.output.json_dict
        elif hasattr(advisor_task.output, 'pydantic') and advisor_task.output.pydantic:
             return advisor_task.output.pydantic.model_dump()
        else:
            # Fallback parsing
            raw_str = str(result)
            return json.loads(raw_str)
    except Exception as e:
        print(f"Error extracting JSON output: {e}")
        return {
            "ticker": ticker,
            "risk_opportunity": str(result),
            "recommendation": "Hold" # fallback
        }
