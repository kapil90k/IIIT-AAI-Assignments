# Roll number: evernorth-aai-1197201
"""Tool declarations exposed by the SkyVault MCP registry."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_flight_status",
            "description": "Returns current status, gate, delay, route and assigned aircraft details for a specific flight number such as AI203.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_num": {"type": "string", "description": "Flight number, e.g., AI203"}
                },
                "required": ["flight_num"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_passenger",
            "description": "Returns booking reference, seat number and destination for a passenger name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "maintenance_history",
            "description": "Returns maintenance inspection and outstanding issues for an aircraft tail number.",
            "parameters": {
                "type": "object",
                "properties": {"tail_number": {"type": "string"}},
                "required": ["tail_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_available_gate",
            "description": "Finds an available gate for the requested terminal.",
            "parameters": {
                "type": "object",
                "properties": {"terminal": {"type": "string"}},
                "required": ["terminal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Returns weather condition, visibility, wind and temperature for an airport code.",
            "parameters": {
                "type": "object",
                "properties": {"airport": {"type": "string"}},
                "required": ["airport"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_aircraft",
            "description": "Returns dimensions, fuel and passenger capacity for an aircraft type.",
            "parameters": {
                "type": "object",
                "properties": {"aircraft_type": {"type": "string"}},
                "required": ["aircraft_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Persist a user fact or preference across process restarts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Stable fact name"},
                    "value": {"description": "Fact or preference value"},
                    "source": {"type": "string", "description": "Origin of the fact"},
                },
                "required": ["key", "value", "source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Search facts and preferences saved in persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Key or natural-language search"}
                },
                "required": ["query"],
            },
        },
    },
]

LAZY_DESCRIPTION_EXAMPLE = "Gets flight info."
CAREFUL_DESCRIPTION_EXAMPLE = (
    "Returns current status, gate, scheduled departure time, delay, route, and assigned aircraft "
    "tail number for a specific flight number (e.g., AI203)."
)

