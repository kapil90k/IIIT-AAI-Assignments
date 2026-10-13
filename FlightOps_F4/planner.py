"""Planning helper for transparent goal/plan output."""

import re


def _extract_flight_number(text):
    match = re.search(r"\b[A-Z]{2}\d{2,4}\b", (text or "").upper())
    return match.group(0) if match else None


def create_goal_and_plan(user_message):
    """Return deterministic plan for delay-risk queries, else lightweight generic plan."""
    query = (user_message or "").strip()
    lower_q = query.lower()

    patterns = [
        "likely to depart",
        "depart on time",
        "delayed",
        "delay risk",
        "operational risk",
    ]
    operational = any(p in lower_q for p in patterns)

    if operational:
        flight = _extract_flight_number(query)
        if flight:
            return {
                "goal": "Determine whether %s is likely to depart on time." % flight,
                "plan": [
                    "Check flight status for %s" % flight,
                    "Check weather at departure airport",
                    "Check maintenance history of assigned aircraft",
                    "Synthesize risk-based conclusion",
                ],
            }

    return {
        "goal": "Answer user question using the minimum required tools.",
        "plan": [
            "Interpret user intent",
            "Call required tools (if needed)",
            "Return concise grounded answer",
        ],
    }

