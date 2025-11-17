import asyncio

from dotenv import load_dotenv

from agents.fact_finder.agent import root_agent


async def main():
    load_dotenv()

    print("TruthLens Fact-Finder (ADK)")
    print("---------------------------")
    user_statement = input("Enter a statement or query about an event: ").strip()

    # run_async returns an async generator -> iterate over it
    print("\n--- Agent Response ---")
    async for step in root_agent.run_async(user_statement):
        # Each step is typically a dict or object representing a turn or output.
        # For now, just print it; we can refine once we see the structure.
        print(step)


if __name__ == "__main__":
    asyncio.run(main())
