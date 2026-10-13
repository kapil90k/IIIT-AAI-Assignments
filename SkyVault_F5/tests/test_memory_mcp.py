# Roll number: evernorth-aai-1197201

import memory
from mcp_client import MCPClient
from mcp_server import MCPServer


def test_memory_persists_and_overwrites(tmp_path, monkeypatch):
    path = tmp_path / "memory.json"
    monkeypatch.setattr(memory, "MEMORY_FILE", path)

    first = memory.remember("preferred terminal", "T1", "test")
    second = memory.remember("preferred terminal", "T2", "test")
    recalled = memory.recall("preferred_terminal")

    assert first["result"]["replaced"] is False
    assert second["result"]["replaced"] is True
    assert recalled["result"]["preferred_terminal"]["value"] == "T2"
    assert path.exists()


def test_mcp_lifecycle_and_eight_tools():
    client = MCPClient()
    tools = client.list_tools()

    assert client.server_info["result"]["serverInfo"]["name"] == "SkyVault MCP Server"
    assert len(tools) == 8
    assert {item["name"] for item in tools} >= {"remember", "recall", "get_weather"}
    assert client.call_tool("get_weather", {"airport": "HYD"})["status"] is True


def test_mcp_errors_have_json_rpc_shape():
    server = MCPServer()
    unknown = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "not_a_tool", "arguments": {}},
        }
    )
    missing = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "get_weather", "arguments": {}},
        }
    )

    assert unknown["error"]["code"] == -32001
    assert missing["error"]["code"] == -32602
