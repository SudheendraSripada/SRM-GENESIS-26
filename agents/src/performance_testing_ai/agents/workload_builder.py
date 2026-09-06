from typing import Optional
from crewai import Agent, LLM

def create_workload_builder_agent(config: dict, llm: Optional[LLM] = None) -> Agent:
    """Creates the Workload Builder Agent (tools strictly omitted for safety; cannot execute code)."""
    return Agent(
        config=config,
        llm=llm,
        verbose=True,
        tools=[],
        allow_delegation=False,
    )
