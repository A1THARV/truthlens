import asyncio

from dotenv import load_dotenv

from google.adk.runner import Runner

from app import app


async def main():
    load_dotenv()

    print("TruthLens Fact-Finder (ADK)")
    print("---------------------------")
    user_statement = input("Enter a statement or query about an event: ").strip()

    runner = Runner(app=app)

    print("\n--- Agent Response ---")

    # Runner.run_async is the recommended entrypoint; it handles context and agent invocation.
    async for step in runner.run_async(
        input=user_statement,
        agent_name="truthlens_fact_finder",  # matches root_agent.name
    ):
        # For now, just print each step; we can refine as we see the shape.
        print(step)


if __name__ == "__main__":
    asyncio.run(main())
