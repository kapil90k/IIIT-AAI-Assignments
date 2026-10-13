# Roll number: evernorth-aai-1197201
"""Independent MCP consumer proving that tools are reusable."""

from mcp_client import MCPClient


def main():
    client = MCPClient()
    print(client.call_tool("find_available_gate", {"terminal": "T2"}))


if __name__ == "__main__":
    main()
