# Roll number: evernorth-aai-1197201
"""Hand-built in-process MCP-style JSON-RPC server."""

from memory import recall, remember
from schemas import TOOL_SCHEMAS
from tools import (
    find_available_gate,
    get_flight_status,
    get_weather,
    lookup_aircraft,
    maintenance_history,
    search_passenger,
)


class ToolRegistry:
    """Own tool metadata and implementations independently of transport."""

    def __init__(self):
        self._functions = {
            "get_flight_status": get_flight_status,
            "search_passenger": search_passenger,
            "maintenance_history": maintenance_history,
            "find_available_gate": find_available_gate,
            "get_weather": get_weather,
            "lookup_aircraft": lookup_aircraft,
            "remember": remember,
            "recall": recall,
        }
        self._schemas = {}
        for declaration in TOOL_SCHEMAS:
            definition = declaration["function"]
            self._schemas[definition["name"]] = {
                "name": definition["name"],
                "description": definition["description"],
                "inputSchema": definition["parameters"],
            }

    def list_tools(self):
        return list(self._schemas.values())

    def execute(self, name, arguments):
        function = self._functions.get(name)
        if function is None:
            raise KeyError("Unknown tool: %s" % name)
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a JSON object")

        schema = self._schemas[name]["inputSchema"]
        missing = [field for field in schema.get("required", []) if field not in arguments]
        if missing:
            raise TypeError("Missing required argument(s): %s" % ", ".join(missing))
        return function(**arguments)


class MCPServer:
    """Validate and dispatch the required MCP JSON-RPC lifecycle."""

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, registry=None):
        self.registry = registry or ToolRegistry()

    @staticmethod
    def _success(request_id, result):
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id, code, message):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def handle(self, request):
        if not isinstance(request, dict):
            return self._error(None, -32600, "Invalid Request")

        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return self._error(request_id, -32600, "Invalid Request")

        method = request["method"]
        params = request.get("params") or {}
        try:
            if method == "initialize":
                return self._success(
                    request_id,
                    {
                        "protocolVersion": self.PROTOCOL_VERSION,
                        "serverInfo": {"name": "SkyVault MCP Server", "version": "1.0.0"},
                        "clientInfo": params.get("clientInfo", {}),
                    },
                )
            if method == "tools/list":
                return self._success(request_id, {"tools": self.registry.list_tools()})
            if method == "tools/call":
                name = params.get("name")
                if not name:
                    return self._error(request_id, -32602, "Missing tool name")
                result = self.registry.execute(name, params.get("arguments", {}))
                return self._success(request_id, result)
            return self._error(request_id, -32601, "Method not found: %s" % method)
        except KeyError as exc:
            return self._error(request_id, -32001, str(exc).strip("'"))
        except TypeError as exc:
            return self._error(request_id, -32602, str(exc))
        except Exception as exc:
            return self._error(request_id, -32000, "Tool execution failed: %s" % exc)
