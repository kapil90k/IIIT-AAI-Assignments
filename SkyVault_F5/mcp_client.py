# Roll number: evernorth-aai-1197201
"""In-process MCP client used by SkyVault and independent consumers."""

import json

from mcp_server import MCPServer


class MCPClient:
    """Send JSON-RPC dictionaries to an MCPServer and retain a full trace."""

    def __init__(self, server=None):
        self.server = server or MCPServer()
        self._next_id = 1
        self.trace = []
        self.server_info = self._request(
            "initialize",
            {
                "protocolVersion": MCPServer.PROTOCOL_VERSION,
                "clientInfo": {"name": "SkyVault Host", "version": "1.0.0"},
            },
        )

    def _request(self, method, params=None):
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params or {},
        }
        self._next_id += 1
        response = self.server.handle(request)
        self.trace.append({"request": request, "response": response})
        return response

    def list_tools(self):
        response = self._request("tools/list")
        if "error" in response:
            raise RuntimeError(response["error"]["message"])
        return response["result"]["tools"]

    def call_tool(self, name, arguments):
        response = self._request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        if "error" in response:
            return {
                "status": False,
                "message": response["error"]["message"],
                "error_code": response["error"]["code"],
            }
        return response["result"]

    def trace_as_jsonl(self):
        lines = []
        for exchange in self.trace:
            lines.append(json.dumps({"direction": "request", **exchange["request"]}))
            lines.append(json.dumps({"direction": "response", **exchange["response"]}))
        return "\n".join(lines)
