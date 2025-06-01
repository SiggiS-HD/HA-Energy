
import sqlite3
import pandas as pd
from influxdb import InfluxDBClient
from datetime import datetime, timezone
from pathlib import Path
import json
from extract_latest_ha_db import extract_latest_ha_db

def load_config():
    with open(Path(__file__).parent / "config.json", "r") as f:
        return json.load(f)

def get_latest_timestamp(influx_client, friendly_name):
    query = f"""SELECT last(\"value\") FROM \"energy\"
WHERE \"entity_id\" = '{friendly_name}'"""
    result = list(influx_client.query(query).get_points())
    if not result:
        return None
    try:
        return datetime.fromisoformat(result[0]['time'].replace('Z', '+00:00'))
    except Exception as e:
        print(f"⚠️ Fehler beim Lesen des Zeitstempels für {friendly_name}: {e}")
        return None

def get_metadata_id(conn, sensor_id):
    result = pd.read_sql_query(
        f"SELECT id FROM statistics_meta WHERE statistic_id = '{sensor_id}'", conn)
    return result.iloc[0]['id'] if not result.empty else None

def detect_sensor_type(df):
    if df.empty or 'state' not in df or 'sum' not in df:
        return "unknown"
    df = df.dropna(subset=['state', 'sum'])
    if df.empty:
        return "unknown"
    ratio = (df['state'] / df['sum']).clip(upper=1)
    return "counter" if (ratio > 0.9).mean() > 0.9 else "delta"

def import_sensor_data(db_path, influx_client, sensor_id, friendly_name, start_date):
    conn = sqlite3.connect(db_path)
    metadata_id = get_metadata_id(conn, sensor_id)
    if metadata_id is None:
        print(f"⚠️ Kein metadata_id für {sensor_id}")
        conn.close()
        return

    query = f"""
            SELECT start_ts, state, sum FROM statistics
            WHERE metadata_id = {metadata_id} AND start_ts > {int(start_date.timestamp())}
            ORDER BY start_ts ASC
            """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print(f"⚠️ Keine neuen Daten für {friendly_name}")
        return

    df['timestamp'] = pd.to_datetime(df['start_ts'], unit='s', utc=True)
    df['state'] = pd.to_numeric(df['state'], errors='coerce')
    df['sum'] = pd.to_numeric(df['sum'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    sensor_type = detect_sensor_type(df)
    if sensor_type == "delta":
        df['value'] = df['state']
    elif sensor_type == "counter":
        df['value'] = df['sum']
    else:
        print(f"⚠️ Unbekannter Sensortyp bei {friendly_name}")
        return

    json_body = [
        {
            "measurement": "energy",
            "tags": {
                "entity_id": friendly_name,
                "sensor_type": sensor_type
            },
            "time": row['timestamp'].isoformat(),
            "fields": {
                "value": float(row['value'])
            }
        }
        for _, row in df.iterrows()
    ]

    if json_body:
        influx_client.write_points(json_body)
        print(f"✅ {len(json_body)} Werte für {friendly_name} importiert.")
    else:
        print(f"⚠️ Keine gültigen Werte für {friendly_name}")

def read_sensor_config(path):
    sensors = []
    with open(path, 'r') as f:
        for line in f:
            if ';' in line:
                sensor_id, friendly_name = line.strip().split(';')
                sensors.append((sensor_id.strip(), friendly_name.strip()))
    return sensors

def main():
    config = load_config()
    db_path = extract_latest_ha_db()
    if not db_path:
        print("❌ Datenbank konnte nicht extrahiert werden.")
        return

    sensor_file_path = Path(__file__).parent / config["sensor_file"]
    if not sensor_file_path.exists():
        print(f"❌ Sensorliste nicht gefunden: {sensor_file_path}")
        return

    sensors = read_sensor_config(sensor_file_path)
    influx_client = InfluxDBClient(
        host=config["influxdb"]["host"],
        port=config["influxdb"]["port"]
    )
    influx_client.switch_database(config["influxdb"]["database"])

    for sensor_id, friendly_name in sensors:
        print(f"🔄 Verarbeite: {friendly_name} ({sensor_id})")
        latest = get_latest_timestamp(influx_client, friendly_name)
        start_date = latest if latest else datetime.fromtimestamp(0, tz=timezone.utc)
        import_sensor_data(db_path, influx_client, sensor_id, friendly_name, start_date)

    print("🏁 Import abgeschlossen.")

if __name__ == "__main__":
    main()
