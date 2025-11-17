from google.adk.app import App

from agents.fact_finder.agent import root_agent


# TruthLens App – currently only the Fact-Finder agent is wired in.
app = App(
    root_agent=root_agent,
)
