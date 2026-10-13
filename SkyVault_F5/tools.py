# Roll number: evernorth-aai-1197201
"""Business tools exposed by the SkyVault MCP server."""

from data import AIRCRAFT, FLIGHTS, GATES, MAINTENANCE, OCCUPIED_GATES, PASSENGERS, WEATHER


def _ok(result):
    return {"status": True, "result": result}


def _error(message):
    return {"status": False, "message": message}


def get_flight_status(flight_num):
    try:
        key = str(flight_num).strip().upper()
        rec = FLIGHTS.get(key)
        if not rec:
            return _error("Flight not found: %s" % key)
        return _ok(rec)
    except Exception as exc:
        return _error("Error occurred: %s" % exc)


def search_passenger(name):
    try:
        key = str(name).strip().lower().replace(" ", "-")
        rec = PASSENGERS.get(key)
        if not rec:
            return _error("Passenger not found: %s" % name)
        return _ok(rec)
    except Exception as exc:
        return _error("Error occurred: %s" % exc)


def maintenance_history(tail_number):
    try:
        key = str(tail_number).strip().upper()
        rec = MAINTENANCE.get(key)
        if not rec:
            return _error("No maintenance data for tail number: %s" % key)
        return _ok(rec)
    except Exception as exc:
        return _error("Error occurred: %s" % exc)


def find_available_gate(terminal):
    try:
        key = str(terminal).strip().upper()
        if key.startswith("TERMINAL "):
            key = "T" + key.split()[-1]
        gates = GATES.get(key)
        if gates is None:
            return _error("Terminal not found: %s" % key)
        for gate in gates:
            if gate not in OCCUPIED_GATES:
                return _ok(gate)
        return _error("No available gate in terminal %s" % key)
    except Exception as exc:
        return _error("Error occurred: %s" % exc)


def get_weather(airport):
    try:
        key = str(airport).strip().upper()
        rec = WEATHER.get(key)
        if not rec:
            return _error("Weather not found for airport: %s" % key)
        return _ok(rec)
    except Exception as exc:
        return _error("Error occurred: %s" % exc)


def lookup_aircraft(aircraft_type):
    try:
        key = str(aircraft_type).strip().upper()
        rec = AIRCRAFT.get(key)
        if not rec:
            return _error("Aircraft type not found: %s" % key)
        return _ok(rec)
    except Exception as exc:
        return _error("Error occurred: %s" % exc)

