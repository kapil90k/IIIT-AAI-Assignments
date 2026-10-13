# Roll number: evernorth-aai-1197201
"""CLI entrypoint for Assignment 05 Project SkyVault."""

import json

from agent import run_agent

# Mandatory marker from the Assignment 05 brief.
heisenberg = "skyvault_submission"


def print_run_output(run_output):
    print("\nGoal:")
    print(run_output["goal"])

    print("\nPlan:")
    for idx, step in enumerate(run_output["plan"], 1):
        print("%d. %s" % (idx, step))

    print("\nTool Calls:")
    if not run_output["tool_journal"]:
        print("(none)")
    else:
        for item in run_output["tool_journal"]:
            print("- %s(%s)" % (item["tool"], json.dumps(item["arguments"])))
            print("  -> %s" % json.dumps(item["result"], ensure_ascii=False))

    print("\nMCP JSON-RPC Trace:")
    for exchange in run_output["mcp_trace"]:
        print("REQUEST  %s" % json.dumps(exchange["request"], ensure_ascii=False))
        print("RESPONSE %s" % json.dumps(exchange["response"], ensure_ascii=False))

    print("\nFinal Answer:")
    print(run_output["answer"])

    print("\nReflection:")
    print(json.dumps(run_output["reflection"], ensure_ascii=False))


def main():
    print("Project SkyVault Assignment CLI")
    print("Type 'exit' to quit.")

    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGood Bye...!")
            break

        if not user_message:
            continue
        if user_message.lower() in ("exit", "quit"):
            print("Good Bye...!")
            break

        try:
            run_output = run_agent(user_message)
            print_run_output(run_output)
        except Exception as exc:
            print("Assistant: {'status': False, 'message': 'Error occurred: %s'}" % exc)


if __name__ == "__main__":
    main()

