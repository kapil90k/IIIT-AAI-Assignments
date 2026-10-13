# FlightOps Submission

FlightOps is an end-to-end implementation for Fortnight Assignment 04.

## Model and provider

- Provider: Ollama (local)
- Model: gemma3:4b
- Provider integration code: `provider.py`

## What is implemented

1. **Tool backend**
   - Mock data in `data.py` for flights, aircraft, passengers, maintenance, weather, and gates.
   - Tools in `tools.py`:
     - `get_flight_status(flight_num)`
     - `search_passenger(name)`
     - `maintenance_history(tail_number)`
     - `find_available_gate(terminal)`
     - `get_weather(airport)`
     - `lookup_aircraft(aircraft_type)`

2. **Tool declarations**
   - JSON schemas in `schemas.py` with name, description, parameters, and required fields.
   - Includes lazy vs careful description examples for report discussion.

3. **Function-calling lifecycle**
   - `agent.py` implements request -> tool call parse -> execute -> return tool output -> continue until final answer.
   - Uses Ollama tool calls when runtime is available.

4. **Multi-tool agent loop**
   - For operational risk questions, executes deterministic chain:
     - flight status -> weather -> maintenance -> synthesized decision.

5. **Planning**
   - `planner.py` prints goal and plan before execution.

6. **Reflection**
   - `reflector.py` critiques tool usage, failures, and confidence.

7. **Error handling**
   - Every tool returns structured errors (`{"status": False, "message": "..."}`).
   - Agent validates tool names/arguments and handles runtime failures.

## Project structure

```text
FlightOps/
|-- main.py
|-- app.py
|-- agent.py
|-- planner.py
|-- reflector.py
|-- provider.py
|-- schemas.py
|-- tools.py
|-- data.py
|-- config.py
|-- .env.example
|-- requirements.txt
|-- tests/
|   |-- test_agent.py
|   `-- test_tools.py
|-- screenshots/
|   `-- README.md
|-- PACKAGING_CHECKLIST.md
`-- REPORT.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Run tests

```bash
pytest -q
```

## Screenshot guidance

Add these files under `screenshots/` before final zip:
- `screenshot_1_multi_tool.png` (show Goal, Plan, 3+ tool calls, Reflection)
- `screenshot_2_error_handling.png` (show structured failure handling)

## Submission name

Zip this folder as:

`FlightOps_KapilKumar.zip`
