import asyncio

from dotenv import load_dotenv

from agents.fact_finder.agent import root_agent


async def run_once():
    load_dotenv()

    print("TruthLens Fact-Finder")
    print("---------------------")
    user_statement = input("Enter a statement or query about an event: ").strip()

    # The exact call depends on ADK's API; adjust once integrated.
    # Many agent frameworks expose an async run / invoke method.
    try:
        result = await root_agent.run(user_statement)  # type: ignore[attr-defined]
    except NotImplementedError as e:
        print("Agent.run is not implemented in the local stub. Integrate with ADK.")
        print(f"Details: {e}")
        return
    except AttributeError:
        print("root_agent.run(...) is not available. Integrate with the real ADK Agent API.")
        return

    print("\n--- Agent Response ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(run_once())
