"""
PHK 180 Local Web Control - Unofficial Community Integration for Home Assistant.

LEGAL DISCLAIMER / HAFTUNGSAUSSCHLUSS:
Dieses Softwareprojekt ist eine unabhängige, private und inoffizielle
Open-Source-Community-Entwicklung unter der MIT-Lizenz.
Es besteht keinerlei wirtschaftliche, organisatorische oder rechtliche
Verbindung zur AEREX HaustechnikSysteme GmbH oder der MAICO-Gruppe.
Marken- und Modellbezeichnungen (wie PHK 180 / PHS 300) werden ausschließlich
als technischer Kompatibilitätshinweis (§ 23 MarkenG) genannt.
Die Nutzung erfolgt vollständig auf eigene Gefahr.
"""

DOMAIN = "phk180"
DEFAULT_HOST = "aerexphk180"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = ""
DEFAULT_SCAN_INTERVAL = 15

PLATFORMS = [
    "sensor",
    "binary_sensor",
    "number",
    "select",
    "switch",
    "button",
    "date",
]

# Technisch zulässige Betriebsgrenzen für Endkunden-Sollwerte:
# Schlüssel: (param_id, param_idx) -> (min_val, max_val, step_size)
PARAMETER_LIMITS = {
    (550, 0): (18.0, 25.0, 0.5),    # Raumsolltemperatur (°C)
    (547, 0): (18.0, 20.0, 1.0),    # Raumabsenkung Ferienbetrieb (°C)
    (551, 0): (-3.0, 3.0, 0.1),     # Abgleich Raumtemperatur (K)
    (553, 0): (-2.0, -0.4, 0.1),    # Einschaltpunkt Zusatzheizung Zuluft (K)
    (561, 0): (2.0, 10.0, 1.0),     # Max. Raumtemperatur Differenz (K, Summe max. 30 °C)
    (951, 0): (30.0, 50.0, 1.0),    # Warmwassersolltemperatur (°C)
    (964, 0): (5.0, 10.0, 1.0),     # WW-Ausschalthysterese Wärmepumpe (K, Summe max. 55 °C)
    (965, 0): (5.0, 15.0, 1.0),     # WW-Ausschalthysterese E-Heizstab (K, Summe max. 60 °C)
    (963, 0): (1.0, 7.0, 1.0),      # Intervall für Legionellenschutz (Tage)
    (230, 0): (5.0, 90.0, 5.0),     # Dauer Lüftungsstufe / Stoßlüftung (min)
    (233, 0): (6.0, 18.0, 1.0),     # Filterstandzeit Außenfilter (Monate)
    (240, 0): (3.0, 8.0, 1.0),      # Filterstandzeit Gerätefilter (Monate)
    (247, 0): (500.0, 900.0, 10.0), # CO2-Grenzwert min (ppm)
    (247, 1): (1000.0, 2000.0, 10.0), # CO2-Grenzwert max (ppm)
    (248, 0): (30.0, 40.0, 1.0),    # Rel. Feuchte-Grenzwert min (%)
    (298, 0): (50.0, 80.0, 1.0),    # Rel. Feuchte-Grenzwert max Winter (%)
    (299, 0): (50.0, 80.0, 1.0),    # Rel. Feuchte-Grenzwert max Sommer (%)
    (452, 0): (0.0, 4.0, 1.0),      # Min. Außentemperatur für EWT Heizen (°C)
    (453, 0): (2.0, 6.0, 1.0),      # Min. Außentemperatur Hysterese für EWT (K)
    (351, 0): (5.0, 20.0, 1.0),     # Min. Lufteintrittstemperatur für EWT Kühlen (°C)
    (456, 0): (2.0, 6.0, 1.0),      # Min. Lufteintrittstemperatur Hysterese für EWT (K)
}
