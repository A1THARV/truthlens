import asyncio

from dotenv import load_dotenv

from agents.fact_finder.agent import root_agent


async def main():
    load_dotenv()

    print("TruthLens Fact-Finder (ADK)")
    print("---------------------------")
    user_statement = input("Enter a statement or query about an event: ").strip()

    # ADK v0.2+ style: use run_async
    # The API generally expects the user input as a string or dict, depending on config.
    result = await root_agent.run_async(user_statement)

    print("\n--- Agent Response ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
