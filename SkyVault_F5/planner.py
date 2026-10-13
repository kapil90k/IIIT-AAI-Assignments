# Roll number: evernorth-aai-1197201
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

    if "remember" in lower_q:
        return {
            "goal": "Persist the requested fact for future SkyVault sessions.",
            "plan": [
                "Extract the fact and stable memory key",
                "Call remember through MCP",
                "Confirm whether the value was stored or replaced",
            ],
        }

    if "gate" in lower_q and not _extract_flight_number(query):
        return {
            "goal": "Find an available gate using explicit or remembered preferences.",
            "plan": [
                "Load persistent terminal preference when needed",
                "Call the gate tool through MCP",
                "Return a grounded gate recommendation",
            ],
        }

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

