# Project SkyVault — Assignment 05

Roll number: `evernorth-aai-1197201`

SkyVault extends the Assignment 04 FlightOps agent with persistent memory and a hand-built, in-process Model Context Protocol (MCP) lifecycle. It uses no agent framework and no MCP SDK.

## What changed since Assignment 04

- `memory.py` stores facts in on-disk JSON, reloads them after restart, and provides `remember` and `recall`.
- `mcp_server.py` separates `ToolRegistry` from `MCPServer` and implements JSON-RPC `initialize`, `tools/list`, and `tools/call`.
- `mcp_client.py` provides the only tool-access path used by `agent.py` and records every request/response.
- `agent.py` is now the MCP Host. It obtains all eight LLM tool declarations from `tools/list`, injects a memory summary into the system prompt, and never imports `tools.py`.
- `gatebot.py` demonstrates a second consumer that accesses a FlightOps tool using only the MCP client.
- The CLI prints the complete MCP JSON-RPC trace alongside Goal, Plan, Tool Calls, Answer, and Reflection.

## Memory conflict-resolution rule

Memory keys are normalized to lowercase snake case. A new fact with the same normalized key overwrites the old value, records a new source and UTC timestamp, and returns `replaced: true`; old and new values are never silently retained together. Different keys remain independent.

By default, memory is stored in `memory_store.json` beside the source files. Set `SKYVAULT_MEMORY_FILE` to use another path.

## Setup and configuration

```bash
pip install -r requirements.txt
ollama pull gemma3:4b
```

The provider is configured only through environment variables:

```text
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
MAX_TOOL_CALLS=8
SKYVAULT_MEMORY_FILE=memory_store.json
```

Do not include a real `.env` in the submission.

## Run

```bash
python main.py
```

Independent MCP consumer:

```bash
python gatebot.py
```

Tests:

```bash
pytest -q
```

## Required demonstrations

Persistent-memory restart:

1. Start `python main.py`.
2. Enter: `I usually work Terminal 2, remember that.`
3. Exit the process completely.
4. Start `python main.py` again.
5. Enter: `Find me an open gate.`
6. The trace shows `recall(preferred_terminal)` followed by `find_available_gate(T2)`.

Multi-tool MCP trace:

```text
Is AI203 likely to depart on time?
```

The CLI displays `initialize`, `tools/list`, and three `tools/call` JSON-RPC exchanges before the grounded answer and reflection.
A captured full run is included in `mcp_trace_sample.jsonl`.

## Project structure

```text
main.py              CLI and JSON-RPC trace display
agent.py             MCP Host, model loop, memory workflows
memory.py            Persistent JSON memory
mcp_server.py        ToolRegistry and MCPServer
mcp_client.py        MCPClient and trace journal
mcp_trace_sample.jsonl Captured complete multi-tool JSON-RPC run
gatebot.py           Optional independent consumer
tools.py/data.py     FlightOps business tools and mock data
schemas.py           Eight MCP/LLM tool contracts
planner.py           Goal and plan generation
reflector.py         Post-run critique
provider.py/config.py Configurable Ollama integration
tests/                Unit and end-to-end tests
```

## Final report

### 1. Two kinds of forgetting

`memory.py` is fixing the first type of forgetting because saved facts does not get lost after program is closed. When we start it again, these facts can be loaded and added in the system prompt. But for 10,000 pilots this simple JSON file will become very big and searching correct pilot memory can be confusing. For that scale we will need proper database, pilot identity, better searching and rules for old or conflicting memories.

### 2. Trust boundary

Before MCP, `agent.py` was directly importing Python tools, so all code was trusting each other inside same process. After MCP, the Host is trusting tool schemas and results given by server, while server also receives arguments from client which may be wrong or harmful. Checks should be added in MCP server before any tool is executed, like authentication, permission, schema validation and rate limit. Host should also checks the returned result before using it in final answer.

### 3. Task handoff

MCP alone is not enough for SkyVault to discuss and negotiate a maintenance work with MaintenanceAgent. MCP mainly helps an agent to discover and call tools, but it does not manage full conversation and task status between two agents. A2A protocol from this fortnight is more suitable because it support agent identity, task handoff, progress and long-running collaboration. So MCP can call the maintenance tools, while A2A can handle the actual agent-to-agent task.

### 4. Framework tradeoff

I selected MCP server as the hand-built component because it helped me understand what is actually happening for every request and response. I can clearly see request ID, JSON-RPC format, tool schema, errors and how registry is separated from server. If I started directly with CrewAI or AutoGen, most of these things will be hidden behind framework functions. Development may become faster, but I would not understand properly where validation happens or why a protocol call is failing.

## Submission

Create `SkyVault_KapilKumar.zip` containing the project files, `.env.example`, tests, and a captured full MCP trace or screenshot. Exclude `.env`, local caches, and personal credentials.
