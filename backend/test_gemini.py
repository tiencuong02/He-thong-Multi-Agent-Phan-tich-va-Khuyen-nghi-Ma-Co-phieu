import os
import asyncio
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

# Find .env in project root (one level up from backend/)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# Force set the environment variable that the native provider expects
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    # Fallback to GEMINI_API_KEY if GOOGLE_API_KEY is not set
    api_key = os.getenv("GEMINI_API_KEY")
    os.environ["GOOGLE_API_KEY"] = api_key or ""

async def test_native_gemini():
    print(f"Loading .env from: {os.path.abspath(env_path)}")
    print(f"API Key present: {bool(os.environ.get('GOOGLE_API_KEY'))}")
    
    if not os.environ.get('GOOGLE_API_KEY'):
        print("ERROR: No API key found. Please check your .env file.")
        return

    print("Testing Native CrewAI Google Provider...")
    
    llm = LLM(
        model="gemini/gemini-2.5-flash"
    )
    
    test_agent = Agent(
        role="Tester",
        goal="Confirm connectivity to Gemini API",
        backstory="A simple testing agent. You respond with 'Hello from Gemini!' and nothing else.",
        llm=llm
    )
    
    test_task = Task(
        description="Confirm you are working by saying exactly 'Hello from Gemini!'",
        expected_output="The string 'Hello from Gemini!'",
        agent=test_agent
    )
    
    crew = Crew(agents=[test_agent], tasks=[test_task])
    
    try:
        # kickoff is a blocking call in current CrewAI version
        result = crew.kickoff()
        print(f"Success! Result: {result}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_native_gemini())
