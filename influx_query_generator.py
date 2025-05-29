
from influxdb import InfluxDBClient
from tkinter import Tk, simpledialog

def get_sensor_type(influx_client, sensor_name):
    query = f"SHOW TAG VALUES FROM energy WITH KEY = \"sensor_type\" WHERE entity_id = '{sensor_name}'"
    result = list(influx_client.query(query).get_points())
    if result:
        return result[0]["value"]
    return None

def generate_influx_query(sensor_name, sensor_type, period="1d", start=None, end=None):
    if not start:
        start = "now() - 30d"
    where_clause = f"WHERE entity_id = '{sensor_name}' AND time >= '{start}'"
    if end:
        where_clause += f" AND time < '{end}'"

    if sensor_type == 'delta':
        return f"SELECT sum(\"value\") AS value FROM energy {where_clause} GROUP BY time({period}) fill(0)"
    elif sensor_type == 'counter':
        return f"SELECT sum(\"difference\") FROM (SELECT DIFFERENCE(last(\"value\")) FROM energy {where_clause} GROUP BY time(1h)) GROUP BY time({period}) fill(0)"
    else:
        raise ValueError("Unbekannter sensor_type: 'delta' oder 'counter' erwartet.")

def main():
    import sys
    root = Tk()
    root.withdraw()

    sensor_name = simpledialog.askstring("Sensor", "Friendly Name in InfluxDB (entity_id):")
    if not sensor_name:
        print("Kein Sensorname angegeben.")
        sys.exit(1)

    period = simpledialog.askstring("Zeitintervall", "Zeitintervall (z. B. 1d, 1h, 1w):", initialvalue="1d")
    start = simpledialog.askstring("Startzeit", "Startzeit (YYYY-MM-DDTHH:MM:SSZ, optional):")
    end = simpledialog.askstring("Endzeit", "Endzeit (YYYY-MM-DDTHH:MM:SSZ, optional):")

    influx_client = InfluxDBClient(host="localhost", port=8086)
    influx_client.switch_database("hadb")

    sensor_type = get_sensor_type(influx_client, sensor_name)
    if not sensor_type:
        print(f"sensor_type für '{sensor_name}' nicht gefunden.")
        sys.exit(1)

    query = generate_influx_query(sensor_name, sensor_type, period=period, start=start, end=end)
    print("\nGenerierte InfluxQL-Abfrage:")
    print(query)

if __name__ == "__main__":
    main()
