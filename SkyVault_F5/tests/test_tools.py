# Roll number: evernorth-aai-1197201

from tools import (
    find_available_gate,
    get_flight_status,
    get_weather,
    lookup_aircraft,
    maintenance_history,
    search_passenger,
)


def test_get_flight_status_success():
    res = get_flight_status("AI203")
    assert res["status"] is True
    assert res["result"]["gate"] == "B12"


def test_get_flight_status_missing():
    res = get_flight_status("AI999")
    assert res["status"] is False


def test_search_passenger_normalization():
    res = search_passenger("Meera Nair")
    assert res["status"] is True
    assert res["result"]["seat"] == "14A"


def test_maintenance_and_weather():
    assert maintenance_history("vt-awx")["status"] is True
    assert get_weather("hyd")["status"] is True


def test_gate_and_aircraft():
    assert find_available_gate("T2") == {"status": True, "result": "B13"}
    assert lookup_aircraft("a320")["status"] is True
