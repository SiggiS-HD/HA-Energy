
from influxdb import InfluxDBClient
import json
from pathlib import Path

def load_config():
    with open(Path(__file__).parent / "config.json", "r") as f:
        return json.load(f)

config = load_config()
client = InfluxDBClient(host=config["influxdb"]["host"], port=config["influxdb"]["port"])

db_name = config["influxdb"]["database"]
existing_dbs = [db['name'] for db in client.get_list_database()]
if db_name in existing_dbs:
    print(f"Die Datenbank '{db_name}' existiert bereits.")
else:
    client.create_database(db_name)
    print(f"Die Datenbank '{db_name}' wurde erstellt.")

print("Verfügbare Datenbanken:")
for db in client.get_list_database():
    print(" -", db['name'])

client.close()
