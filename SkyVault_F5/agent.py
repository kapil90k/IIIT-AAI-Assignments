# Roll number: evernorth-aai-1197201
"""SkyVault host: planning, MCP tool loop, memory, and reflection."""

import json
import re

from config import MAX_TOOL_CALLS
from mcp_client import MCPClient
from memory import memory_summary
from planner import create_goal_and_plan
from provider import chat, get_message_and_tool_calls
from reflector import reflect_run


def _system_prompt(memory_context):
    return (
        "You are SkyVault, an airline operations assistant with persistent memory. "
        "Use tools when operational data or saved facts are needed. "
        "Use remember when the user explicitly asks you to retain a fact. "
        "If you call a tool, provide valid tool arguments only.\n\n"
        "Persistent memory loaded at run start:\n%s" % memory_context
    )


def _extract_flight_number(text):
    match = re.search(r"\b[A-Z]{2}\d{2,4}\b", (text or "").upper())
    return match.group(0) if match else None


def _is_operational_question(text):
    q = (text or "").lower()
    keys = ["depart on time", "likely to depart", "delayed", "delay risk", "operational risk"]
    return any(k in q for k in keys)


def execute_tool(tool_name, arguments, client=None):
    """Execute a tool only through MCP, with structured error output."""
    if not isinstance(arguments, dict):
        return {"status": False, "message": "Tool arguments must be a JSON object"}
    try:
        result = (client or MCPClient()).call_tool(tool_name, arguments)
        if result.get("error_code") == -32602:
            result["message"] = "Invalid tool arguments: %s" % result["message"]
        return result
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


def run_operational_chain(user_message, client):
    """Deterministic multi-tool chain for critical operational assessment."""
    tool_journal = []
    flight_num = _extract_flight_number(user_message)
    if not flight_num:
        return {
            "answer": "Please provide a valid flight number (for example: AI203).",
            "tool_journal": tool_journal,
        }

    first = execute_tool("get_flight_status", {"flight_num": flight_num}, client)
    tool_journal.append({"tool": "get_flight_status", "arguments": {"flight_num": flight_num}, "result": first})

    origin = ""
    tail = ""
    if first.get("status"):
        origin = first["result"].get("origin", "")
        tail = first["result"].get("tail_number", "")

    second = execute_tool("get_weather", {"airport": origin}, client) if origin else {"status": False, "message": "Origin not available"}
    third = execute_tool("maintenance_history", {"tail_number": tail}, client) if tail else {"status": False, "message": "Tail number not available"}

    tool_journal.append({"tool": "get_weather", "arguments": {"airport": origin}, "result": second})
    tool_journal.append({"tool": "maintenance_history", "arguments": {"tail_number": tail}, "result": third})

    answer = _synthesize_operational_answer(first, second, third)
    return {"answer": answer, "tool_journal": tool_journal}


def _model_tool_declarations(mcp_tools):
    return [
        {
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item["description"],
                "parameters": item["inputSchema"],
            },
        }
        for item in mcp_tools
    ]


def run_model_tool_loop(user_message, client, mcp_tools, memory_context):
    """Generic function-calling loop with model-selected tools."""
    messages = [
        {"role": "system", "content": _system_prompt(memory_context)},
        {"role": "user", "content": user_message},
    ]
    declarations = _model_tool_declarations(mcp_tools)

    tool_journal = []
    for _ in range(MAX_TOOL_CALLS):
        response = chat(messages, tools=declarations)
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

            result = execute_tool(tool_name, arguments, client)
            tool_journal.append({"tool": tool_name, "arguments": arguments, "result": result})

            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            messages.append(_format_tool_message(tool_name, result))

    return {
        "answer": "I could not complete the request because the tool-call limit was reached.",
        "tool_journal": tool_journal,
    }


def _extract_terminal(text):
    match = re.search(r"\b(?:terminal\s*)?([123])\b", (text or "").lower())
    return "T" + match.group(1) if match else None


def _is_memory_statement(text):
    lower_q = (text or "").lower()
    return "remember" in lower_q and "terminal" in lower_q


def _is_implicit_gate_question(text):
    lower_q = (text or "").lower()
    return "gate" in lower_q and _extract_terminal(text) is None


def run_memory_chain(user_message, client):
    """Store or use the terminal preference through MCP memory tools."""
    tool_journal = []
    if _is_memory_statement(user_message):
        terminal = _extract_terminal(user_message)
        if not terminal:
            return {"answer": "Which terminal should I remember?", "tool_journal": tool_journal}
        arguments = {"key": "preferred_terminal", "value": terminal, "source": "user"}
        result = execute_tool("remember", arguments, client)
        tool_journal.append({"tool": "remember", "arguments": arguments, "result": result})
        answer = (
            "I will remember that your preferred terminal is %s." % terminal
            if result.get("status")
            else "I could not save that preference: %s" % result.get("message")
        )
        return {"answer": answer, "tool_journal": tool_journal}

    recall_args = {"query": "preferred_terminal"}
    recalled = execute_tool("recall", recall_args, client)
    tool_journal.append({"tool": "recall", "arguments": recall_args, "result": recalled})
    if not recalled.get("status"):
        return {
            "answer": "Please specify a terminal because no terminal preference is stored.",
            "tool_journal": tool_journal,
        }
    terminal = recalled["result"]["preferred_terminal"]["value"]
    gate_args = {"terminal": terminal}
    gate = execute_tool("find_available_gate", gate_args, client)
    tool_journal.append({"tool": "find_available_gate", "arguments": gate_args, "result": gate})
    answer = (
        "Using your saved %s preference, available gate %s is open." % (terminal, gate["result"])
        if gate.get("status")
        else "I recalled %s but could not find a gate: %s" % (terminal, gate.get("message"))
    )
    return {"answer": answer, "tool_journal": tool_journal}


def run_rule_based_fallback(user_message, client):
    """Fallback if model runtime is unavailable during local testing."""
    text = (user_message or "").lower()
    tool_journal = []

    terminal = _extract_terminal(text)
    if "gate" in text and terminal:
        result = execute_tool("find_available_gate", {"terminal": terminal}, client)
        tool_journal.append({"tool": "find_available_gate", "arguments": {"terminal": terminal}, "result": result})
        if result.get("status"):
            return {"answer": "Available gate in %s is %s." % (terminal, result.get("result")), "tool_journal": tool_journal}
        return {"answer": "I could not find an available gate in %s." % terminal, "tool_journal": tool_journal}

    return {"answer": "Model runtime is unavailable and no deterministic fallback matched this query.", "tool_journal": tool_journal}


def run_agent(user_message):
    """Main orchestration entry point for one user turn."""
    memory_context = memory_summary()
    plan = create_goal_and_plan(user_message)
    client = MCPClient()
    mcp_tools = client.list_tools()

    if _is_operational_question(user_message):
        run = run_operational_chain(user_message, client)
    elif _is_memory_statement(user_message) or _is_implicit_gate_question(user_message):
        run = run_memory_chain(user_message, client)
    else:
        try:
            run = run_model_tool_loop(user_message, client, mcp_tools, memory_context)
        except Exception:
            run = run_rule_based_fallback(user_message, client)

    reflection = reflect_run(user_message, run["tool_journal"], run["answer"])
    return {
        "goal": plan["goal"],
        "plan": plan["plan"],
        "tool_journal": run["tool_journal"],
        "mcp_trace": client.trace,
        "reflection": reflection,
        "answer": run["answer"],
    }
