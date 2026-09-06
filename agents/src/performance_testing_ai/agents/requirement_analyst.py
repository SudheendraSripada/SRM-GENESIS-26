from typing import Optional
from crewai import Agent, LLM

def create_requirement_analyst_agent(config: dict, llm: Optional[LLM] = None) -> Agent:
    """Creates the Requirement Analyst Agent (tools strictly omitted for safety)."""
    return Agent(
        config=config,
        llm=llm,
        verbose=True,
        tools=[],
        allow_delegation=False,
    )
