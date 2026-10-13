"""Core FlightOps agent: tool loop, planning, and reflection."""

import json
import re

from config import MAX_TOOL_CALLS
from planner import create_goal_and_plan
from provider import chat, get_message_and_tool_calls
from reflector import reflect_run
from schemas import TOOL_SCHEMAS
from tools import (
    find_available_gate,
    get_flight_status,
    get_weather,
    lookup_aircraft,
    maintenance_history,
    search_passenger,
)

TOOL_FUNCTIONS = {
    "get_flight_status": get_flight_status,
    "search_passenger": search_passenger,
    "maintenance_history": maintenance_history,
    "find_available_gate": find_available_gate,
    "get_weather": get_weather,
    "lookup_aircraft": lookup_aircraft,
}

SYSTEM_PROMPT = (
    "You are FlightOps, an airline operations assistant. "
    "Use tools when operational data is needed. "
    "If you call a tool, provide valid tool arguments only."
)


def _extract_flight_number(text):
    match = re.search(r"\b[A-Z]{2}\d{2,4}\b", (text or "").upper())
    return match.group(0) if match else None


def _is_operational_question(text):
    q = (text or "").lower()
    keys = ["depart on time", "likely to depart", "delayed", "delay risk", "operational risk"]
    return any(k in q for k in keys)


def execute_tool(tool_name, arguments):
    """Validate and execute tools with structured error output."""
    function = TOOL_FUNCTIONS.get(tool_name)
    if function is None:
        return {"status": False, "message": "Unknown tool: %s" % tool_name}

    if not isinstance(arguments, dict):
        return {"status": False, "message": "Tool arguments must be a JSON object"}

    try:
        return function(**arguments)
    except TypeError as exc:
        return {"status": False, "message": "Invalid tool arguments: %s" % exc}
    except Exception as exc:
        return {"status": False, "message": "Tool execution failed: %s" % exc}


def _format_tool_message(tool_name, result):
    return {
        "role": "tool",
        "name": tool_name,
        "content": json.dumps(result),
    }


def _synthesize_operational_answer(flight_result, weather_result, maintenance_result):
    if not flight_result.get("status"):
        return "I could not assess departure risk because flight status is unavailable."

    details = flight_result.get("result", {})
    delay = int(details.get("delay_minutes", 0) or 0)
    weather = weather_result.get("result", {}) if weather_result.get("status") else {}
    maintenance = maintenance_result.get("result", {}) if maintenance_result.get("status") else {}

    risks = []
    if delay > 0:
        risks.append("current schedule already shows a %d minute delay" % delay)
    if weather:
        if str(weather.get("condition", "")).lower() in ("fog", "storm", "rain showers"):
            risks.append("weather at origin (%s) is %s" % (details.get("origin", "N/A"), weather.get("condition")))
        if float(weather.get("visibility_km", 99)) < 3:
            risks.append("visibility is low (%.1f km)" % float(weather.get("visibility_km")))
    if maintenance:
        issues = maintenance.get("outstanding_issues", [])
        if issues:
            risks.append("aircraft has %d open maintenance issue(s)" % len(issues))

    if not risks:
        return (
            "Based on current status, weather, and maintenance records, the flight appears likely "
            "to depart on time."
        )

    return "The flight has operational delay risk because " + "; ".join(risks) + "."


def run_operational_chain(user_message):
    """Deterministic multi-tool chain for critical operational assessment."""
    tool_journal = []
    flight_num = _extract_flight_number(user_message)
    if not flight_num:
        return {
            "answer": "Please provide a valid flight number (for example: AI203).",
            "tool_journal": tool_journal,
        }

    first = execute_tool("get_flight_status", {"flight_num": flight_num})
    tool_journal.append({"tool": "get_flight_status", "arguments": {"flight_num": flight_num}, "result": first})

    origin = ""
    tail = ""
    if first.get("status"):
        origin = first["result"].get("origin", "")
        tail = first["result"].get("tail_number", "")

    second = execute_tool("get_weather", {"airport": origin}) if origin else {"status": False, "message": "Origin not available"}
    third = execute_tool("maintenance_history", {"tail_number": tail}) if tail else {"status": False, "message": "Tail number not available"}

    tool_journal.append({"tool": "get_weather", "arguments": {"airport": origin}, "result": second})
    tool_journal.append({"tool": "maintenance_history", "arguments": {"tail_number": tail}, "result": third})

    answer = _synthesize_operational_answer(first, second, third)
    return {"answer": answer, "tool_journal": tool_journal}


def run_model_tool_loop(user_message):
    """Generic function-calling loop with model-selected tools."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    tool_journal = []
    for _ in range(MAX_TOOL_CALLS):
        response = chat(messages, tools=TOOL_SCHEMAS)
        content, tool_calls = get_message_and_tool_calls(response)

        if not tool_calls:
            answer = content or "I could not produce a final answer."
            return {"answer": answer, "tool_journal": tool_journal}

        for call in tool_calls:
            function_block = call.get("function", {}) if isinstance(call, dict) else getattr(call, "function", {})
            tool_name = function_block.get("name") if isinstance(function_block, dict) else getattr(function_block, "name", "")
            raw_args = function_block.get("arguments", {}) if isinstance(function_block, dict) else getattr(function_block, "arguments", {})

            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except Exception:
                    arguments = {}
            else:
                arguments = raw_args or {}

            result = execute_tool(tool_name, arguments)
            tool_journal.append({"tool": tool_name, "arguments": arguments, "result": result})

            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            messages.append(_format_tool_message(tool_name, result))

    return {
        "answer": "I could not complete the request because the tool-call limit was reached.",
        "tool_journal": tool_journal,
    }


def run_rule_based_fallback(user_message):
    """Fallback if model runtime is unavailable during local testing."""
    text = (user_message or "").lower()
    tool_journal = []

    if "gate" in text and "t2" in text:
        result = execute_tool("find_available_gate", {"terminal": "T2"})
        tool_journal.append({"tool": "find_available_gate", "arguments": {"terminal": "T2"}, "result": result})
        if result.get("status"):
            return {"answer": "Available gate in T2 is %s." % result.get("result"), "tool_journal": tool_journal}
        return {"answer": "I could not find an available gate in T2.", "tool_journal": tool_journal}

    return {"answer": "Model runtime is unavailable and no deterministic fallback matched this query.", "tool_journal": tool_journal}


def run_agent(user_message):
    """Main orchestration entry point for one user turn."""
    plan = create_goal_and_plan(user_message)

    if _is_operational_question(user_message):
        run = run_operational_chain(user_message)
    else:
        try:
            run = run_model_tool_loop(user_message)
        except Exception:
            run = run_rule_based_fallback(user_message)

    reflection = reflect_run(user_message, run["tool_journal"], run["answer"])
    return {
        "goal": plan["goal"],
        "plan": plan["plan"],
        "tool_journal": run["tool_journal"],
        "reflection": reflection,
        "answer": run["answer"],
    }
