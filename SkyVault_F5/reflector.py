# Roll number: evernorth-aai-1197201
"""Reflection helper to critique tool usage after final answer."""


def reflect_run(question, tool_journal, final_answer):
    missing_errors = [item for item in tool_journal if not item.get("result", {}).get("status", False)]
    unnecessary = []
    if "passenger" not in (question or "").lower():
        for item in tool_journal:
            if item.get("tool") == "search_passenger":
                unnecessary.append("search_passenger")

    confidence = "high" if (tool_journal and not missing_errors) else "medium" if tool_journal else "low"

    notes = []
    if unnecessary:
        notes.append("Potentially unnecessary tool(s): %s." % ", ".join(sorted(set(unnecessary))))
    if missing_errors:
        notes.append("One or more tools failed; answer may be incomplete.")
    if not notes:
        notes.append("Tool usage was relevant and sufficient for available mock data.")

    return {
        "confidence": confidence,
        "tool_calls_count": len(tool_journal),
        "reflection": " ".join(notes),
        "final_answer_length": len(final_answer or ""),
    }

