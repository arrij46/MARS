# run_workflow.py
# Terminal-based workflow trigger
import asyncio
from orchestrator.orchestrator import run_workflow


async def main():
    print("\n" + "=" * 60)
    print("MARS FYP - Terminal Workflow Trigger")
    print("=" * 60)
    print("\nStarting workflow...\n")
    
    try:
        await run_workflow()
        print("\n" + "=" * 60)
        print("Workflow completed successfully!")
        print("=" * 60 + "\n")
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
    except Exception as e:
        print(f"\n\nError running workflow: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

