# Roll number: evernorth-aai-1197201
"""Mock backend datasets for the SkyVault assignment."""

FLIGHTS = {
    "AI203": {
        "status": "Delayed",
        "gate": "B12",
        "departure_time": "2026-08-24 19:05",
        "delay_minutes": 35,
        "origin": "HYD",
        "destination": "DEL",
        "tail_number": "VT-KRA",
        "aircraft_type": "A320",
    },
    "AI404": {
        "status": "Scheduled",
        "gate": "A06",
        "departure_time": "2026-08-24 16:55",
        "delay_minutes": 0,
        "origin": "DEL",
        "destination": "BOM",
        "tail_number": "VT-NQD",
        "aircraft_type": "A321",
    },
    "AI512": {
        "status": "Boarding",
        "gate": "C04",
        "departure_time": "2026-08-24 13:20",
        "delay_minutes": 0,
        "origin": "BLR",
        "destination": "HYD",
        "tail_number": "VT-LSM",
        "aircraft_type": "B737-800",
    },
    "AI778": {
        "status": "Scheduled",
        "gate": "B15",
        "departure_time": "2026-08-24 21:40",
        "delay_minutes": 10,
        "origin": "BOM",
        "destination": "CCU",
        "tail_number": "VT-YTR",
        "aircraft_type": "A320",
    },
}

PASSENGERS = {
    "meera-nair": {"booking_reference": "AZ9R4N", "seat": "14A", "destination": "DEL"},
    "arjun-menon": {"booking_reference": "QM7P2K", "seat": "21C", "destination": "BOM"},
    "sana-khan": {"booking_reference": "LX3D8W", "seat": "7F", "destination": "HYD"},
    "dev-patel": {"booking_reference": "TR5H1B", "seat": "3A", "destination": "CCU"},
}

MAINTENANCE = {
    "VT-KRA": {
        "last_inspection_date": "2026-08-22",
        "hours_flown": 9542,
        "outstanding_issues": [
            "Auxiliary fuel pump vibration check pending",
            "Nose-wheel steering calibration due",
        ],
    },
    "VT-AWX": {
        "last_inspection_date": "2026-08-22",
        "hours_flown": 9542,
        "outstanding_issues": [
            "Auxiliary fuel pump vibration check pending",
            "Nose-wheel steering calibration due",
        ],
    },
    "VT-NQD": {
        "last_inspection_date": "2026-08-24",
        "hours_flown": 12014,
        "outstanding_issues": [],
    },
    "VT-LSM": {
        "last_inspection_date": "2026-08-20",
        "hours_flown": 6815,
        "outstanding_issues": ["Cabin pressure sensor replacement scheduled"],
    },
    "VT-YTR": {
        "last_inspection_date": "2026-08-19",
        "hours_flown": 10190,
        "outstanding_issues": ["Brake cooling fan inspection open"],
    },
}

WEATHER = {
    "HYD": {"visibility_km": 2.4, "wind_kmh": 24, "temperature_c": 26, "condition": "Haze"},
    "DEL": {"visibility_km": 7.2, "wind_kmh": 17, "temperature_c": 32, "condition": "Clear"},
    "BLR": {"visibility_km": 9.6, "wind_kmh": 10, "temperature_c": 22, "condition": "Partly cloudy"},
    "BOM": {"visibility_km": 4.1, "wind_kmh": 27, "temperature_c": 29, "condition": "Rain showers"},
    "CCU": {"visibility_km": 6.3, "wind_kmh": 19, "temperature_c": 30, "condition": "Cloudy"},
}

GATES = {
    "T1": ["A01", "A02", "A03", "A04", "A05", "A06", "A07"],
    "T2": ["B10", "B11", "B12", "B13", "B14", "B15", "B16"],
    "T3": ["C01", "C02", "C03", "C04", "C05", "C06"],
}

OCCUPIED_GATES = {"A01", "A03", "A06", "B10", "B11", "B12", "B15", "C01", "C04"}

AIRCRAFT = {
    "A320": {"length_m": 37.57, "wingspan_m": 35.8, "capacity": 186, "fuel_capacity_l": 24210},
    "A321": {"length_m": 44.51, "wingspan_m": 35.8, "capacity": 228, "fuel_capacity_l": 32000},
    "B737-800": {"length_m": 39.5, "wingspan_m": 35.8, "capacity": 189, "fuel_capacity_l": 26020},
    "B787-9": {"length_m": 62.8, "wingspan_m": 60.1, "capacity": 296, "fuel_capacity_l": 126372},
}
