# Roll number: evernorth-aai-1197201
"""One small command-line entry point for every capability."""

import argparse
import json
import os
import re
import subprocess
import sys

from config import OUTBOX_DIR, TRACE_FILE
from mail_store import load_messages
from memory import save_preference
from pipeline import clear_trace, run_capability


CAPABILITIES = ["R1", "R2", "R3", "R4", "R5", "R6", "X1", "X2", "X3"]


def print_result(capability, result):
    if capability == "R1":
        for item in result["decisions"]:
            print(
                "%s | %-8s | %-8s | %s"
                % (
                    item["message_id"],
                    item["disposition"],
                    item["route"],
                    item["reason"],
                )
            )
        print("messages:", len(result["messages"]))
        print("rule handled:", result["metrics"]["rule_handled"])
        print("undecided:", result["metrics"]["undecided"])
    elif capability in {"R2", "R4"}:
        for draft in result["drafts"]:
            print("draft for:", draft["message_id"])
            print("to:", draft["to"])
            print("cited:", draft["cited_message_ids"])
            print(draft["body"])
    elif capability == "R3":
        print(json.dumps(result["metrics"]["gate_results"], indent=2))
        print("outbox writes:", len(list(OUTBOX_DIR.glob("*.json"))))
    elif capability == "R5":
        for flag in result["flags"]:
            if flag["category"] == "prompt_injection":
                print(
                    "FLAGGED: %s attempted to %s; %s"
                    % (flag["message_id"], flag["attempted"], flag["response"])
                )
    elif capability == "R6":
        conflicts = {
            item["conflict"]
            for item in result["commitments"]
            if item["conflict"]
        }
        print("dashboard.html written with exactly three panes.")
        print("commitments:", len(result["commitments"]))
        print("conflicts:", sorted(conflicts))
    elif capability == "X1":
        print(json.dumps(result["metrics"]["sender_lookup"], indent=2))
    elif capability == "X2":
        print(json.dumps(result["metrics"]["follow_ups"], indent=2))
    elif capability == "X3":
        print(json.dumps(result["metrics"]["digest"], indent=2))
    print("reflection:", result["reflection"])


def run_restart_demo():
    """Use two child processes so the first process really exits."""
    first = subprocess.run(
        [sys.executable, __file__, "--r4-store"],
        check=True,
        text=True,
        capture_output=True,
    )
    second = subprocess.run(
        [sys.executable, __file__, "--r4-apply"],
        check=True,
        text=True,
        capture_output=True,
    )
    print(first.stdout.strip())
    print(second.stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", choices=CAPABILITIES)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sender", default="priya@paperjet.io")
    parser.add_argument("--r4-store", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--r4-apply", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.r4_store:
        source = next(
            message for message in load_messages() if message["id"] == "m041"
        )
        match = re.search(
            r"before\s+(\d{1,2}:\d{2})(?:am|pm)",
            source["body"],
            re.IGNORECASE,
        )
        if not match:
            raise ValueError("m041 does not contain the expected meeting preference")
        save_preference(
            "no_meetings_before",
            match.group(1),
            source["id"],
        )
        TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with TRACE_FILE.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "cap": "R4",
                        "event": "preference_saved_in_process",
                        "message_id": source["id"],
                        "process_id": os.getpid(),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        print("Read m041 and stored its preference in process", os.getpid())
        return
    if args.r4_apply:
        result = run_capability("R4", dry_run=True)
        print("Loaded preference in fresh process", os.getpid())
        print_result("R4", result)
        return
    if not args.cap and not args.all:
        parser.error("choose --cap ID or --all")

    clear_trace()
    selected = CAPABILITIES if args.all else [args.cap]
    for capability in selected:
        print("\n=== %s ===" % capability)
        if capability == "R4":
            run_restart_demo()
            continue
        result = run_capability(
            capability,
            dry_run=args.dry_run or (args.all and capability == "R3"),
            sender=args.sender,
        )
        print_result(capability, result)


if __name__ == "__main__":
    main()
