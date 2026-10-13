# Roll number: evernorth-aai-1197201

from agent import execute_tool, run_agent


def test_execute_tool_unknown():
    res = execute_tool("bad_tool", {})
    assert res["status"] is False


def test_execute_tool_argument_error():
    res = execute_tool("get_weather", {})
    assert res["status"] is False
    assert "Invalid tool arguments" in res["message"]


def test_operational_chain_uses_three_tools():
    run = run_agent("Is AI203 likely to depart on time?")
    tools = [x["tool"] for x in run["tool_journal"]]
    assert tools == ["get_flight_status", "get_weather", "maintenance_history"]
    assert isinstance(run["answer"], str)
    assert len(run["answer"]) > 0


def test_run_agent_returns_reflection():
    run = run_agent("Find me an available gate in T2")
    assert "reflection" in run
    assert "confidence" in run["reflection"]

