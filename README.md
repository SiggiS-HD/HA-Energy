# hadb – Energieverbrauchsanalyse mit Home Assistant und InfluxDB

## 📘 Projektbeschreibung

**hadb** ist eine Python-basierte Anwendung zur Analyse des Energieverbrauchs. Sie extrahiert Verbrauchsdaten aus einem Home Assistant Full Backup und überträgt diese in eine InfluxDB zur späteren Visualisierung. Die Daten werden in einer interaktiven Weboberfläche mit Hilfe von APEX-Charts dargestellt.

### 🔄 Workflow

1. **Backup-Extraktion**: Das Skript `extract_latest_ha_db.py` kopiert die Datei `home-assistant_v2.db` aus dem aktuellsten Home Assistant Full Backup ins Projektverzeichnis `SQLite`.
2. **Datenübertragung**: Das Skript `ha_to_influx.py` liest definierte Sensoren aus `sensorliste.txt` und schreibt deren Energieverbrauchsdaten in die InfluxDB `hadb`. Die Influx Datenbank mit den Sensordaten wird in  `\\CL10NAS\web\ha\influxdb` gespeichert.
3. **Visualisierung**: Die Flask-Anwendung `drilldown_full_app.py` stellt die Verbrauchsdaten grafisch in Tages-, Monats- und Jahresansichten dar.

Alle Pfade und Parameter werden zentral über die Datei `config.json` verwaltet.

---

## 🔧 Voraussetzungen

- Python 3.10 oder neuer
- InfluxDB 1.8 (läuft in einem Docker-Container auf dem Server `CL10NAS`)
- Zugriff auf Home Assistant Backups auf `\\CL10NAS\web\ha`

---

## 📦 Installation

### 1. Projekt klonen oder entpacken

```bash
git clone https://github.com/SiggiS-HD/HA-Energy.git hadb
cd hadb
```

Oder ZIP-Datei entpacken und in das Verzeichnis wechseln.

### 2. Python-Umgebung einrichten

```bash
python -m venv venv
source venv/bin/activate  # unter Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Konfiguration anpassen

Bearbeite die Datei `config.json`, um folgende Parameter zu setzen:

```json
{
  "backup_dir": "\\\\CL10NAS\\web\\ha",
  "sqlite_dir": "SQLite",
  "sensor_file": "sensorliste.txt",
  "influxdb": {
    "host": "CL10NAS",
    "port": 8086,
    "database": "hadb"
  }
}
```

---

## 🐳 InfluxDB im Docker-Container starten

```bash
docker run -d \
  --name influxdb \
  -p 8086:8086 \
  -v /pfad/zum/influxdb/data:/var/lib/influxdb \
  influxdb:1.8
```

---

## 🚀 Anwendung starten

### 1. InfluxDB-Datenbank anlegen

```bash
python create_influxdb_hadb.py
```

### 2. Letztes HA-Backup extrahieren und Verbrauchsdaten in InfluxDB schreiben

```bash
python ha_to_influx.py
```

### 3. Web-Anwendung starten

```bash
python drilldown_full_app.py
```

Die Anwendung ist dann unter `http://127.0.0.1:5000` erreichbar.

---

## 📊 Visualisierung

Die Anwendung verwendet folgende HTML-Vorlagen:

- `drilldown_day.html` – Tagesansicht
- `drilldown_month.html` – Monatsansicht
- `drilldown_year.html` – Jahresansicht

---

## 📁 Projektstruktur

```
hadb/
├── SQLite/                      # Enthält extrahierte home-assistant_v2.db
├── templates/                   # HTML-Vorlagen für Charts
├── sensorliste.txt              # Liste der Sensoren
├── config.json                  # Zentrale Konfigurationsdatei
├── create_influxdb_hadb.py      # Erstellt die InfluxDB
├── extract_latest_ha_db.py      # Extrahiert Home Assistant DB aus Backup
├── ha_to_influx.py              # Überträgt Daten in InfluxDB
├── drilldown_full_app.py        # Flask Web-App zur Visualisierung
├── requirements.txt             # Abhängigkeiten
```

---

## 🧩 Lizenz

Dieses Projekt steht unter keiner spezifischen Lizenz. Nutzung auf eigenes Risiko.

---

## 🧑‍💻 Autor

Siegfried Schmidt
