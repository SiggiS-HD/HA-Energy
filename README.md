# hadb – Energieverbrauchsanalyse mit Home Assistant und InfluxDB

## 📘 Projektbeschreibung

**hadb** ist eine Python-basierte Anwendung zur Analyse des Energieverbrauchs. Sie extrahiert Verbrauchsdaten aus einem Home Assistant Full Backup und überträgt diese in eine InfluxDB zur späteren Visualisierung. Die Daten werden in einer interaktiven Weboberfläche mit Hilfe von APEX-Charts dargestellt.

### 🔄 Workflow

1. **Backup-Extraktion**: Das Skript `extract_latest_ha_db.py` kopiert die Datei `home-assistant_v2.db` aus dem aktuellsten Home Assistant Full Backup ins Projektverzeichnis `SQLite`.
2. **Datenübertragung**: Das Skript `ha_to_influx.py` liest definierte Sensoren aus `sensorliste.txt` und schreibt deren Energieverbrauchsdaten in die InfluxDB `hadb`. Die Influx Datenbank mit den Sensordaten wird in  `\\CL10NAS\web\ha\influxdb` gespeichert.
3. **Visualisierung**: Die Flask-Anwendung `energy_dashboard.py` stellt die Verbrauchsdaten grafisch in Tages-, Monats- und Jahresansichten dar. In jeder Ansicht ist es möglich sich den Gesamtverbrauch der Einzelgeräte anzeigen zu lassen.

Alle Pfade und Parameter werden zentral über die Datei `config.json` verwaltet.

---

## 🔧 Voraussetzungen

- Python 3.10 oder neuer
- InfluxDB 1.8 (läuft in einem Docker-Container auf dem Server `CL10NAS`)
- Zugriff auf Home Assistant Backups auf `\\CL10NAS\web\ha`

---

## 📦 Installation

### 📂 NAS-Zugriff unter Ubuntu
# Zugriff auf Synology NAS-Freigabe `\\CL10NAS\web\ha` von Ubuntu

Folgende Schritte sind notwendig, um von einem Ubuntu-System aus auf die Netzwerkfreigabe `\\CL10NAS\web\ha` zuzugreifen. Ziel ist es, die Freigabe dauerhaft oder temporär unter `/mnt/cl10nas/ha` zu mounten.

---

## 🔧 Voraussetzungen

- Ubuntu System mit Internetverbindung
- Zugang zur Synology NAS (`CL10NAS`) mit gültigem Benutzerkonto
- Die Freigabe `web` auf der NAS muss SMB aktiviert haben

---

## 1. 📦 Erforderliche Pakete installieren

```bash
sudo apt update
sudo apt install cifs-utils smbclient
```

---

## 2. 📁 Mount-Verzeichnis anlegen

```bash
sudo mkdir -p /mnt/cl10nas/ha
```

---

## 3. 📡 Verbindung testen (optional, aber empfohlen)

Liste verfügbare Freigaben auf der NAS:

```bash
smbclient -L //CL10NAS -U dein_benutzername
```

Gib das Passwort bei Aufforderung ein.

---

## 4. 📥 Temporärer Mount

```bash
sudo mount -t cifs //CL10NAS/web/ha /mnt/cl10nas/ha \
  -o username=dein_benutzername,password='dein_passwort',iocharset=utf8,file_mode=0777,dir_mode=0777
```

> Hinweis: Falls dein Passwort Sonderzeichen wie `!` enthält, **unbedingt in einfache Hochkommas setzen**.

Alternativ (sicherer): Erstelle eine Datei mit Zugangsdaten:

```bash
sudo nano /etc/samba/credentials_cl10nas
```

Inhalt:

```
username=dein_benutzername
password=dein_passwort
```
In der Datei `/etc/samba/credentials_cl10nas` darf das Passwort nicht in Hochkommas `('...' oder "...")` gesetzt werden.

Datei absichern:

```bash
sudo chmod 600 /etc/samba/credentials_cl10nas
```

Dann mounten mit:

```bash
sudo mount -t cifs //CL10NAS/web/ha /mnt/cl10nas/ha \
  -o credentials=/etc/samba/credentials_cl10nas,iocharset=utf8,file_mode=0777,dir_mode=0777
```

---

## 5. 🔁 Automatischer Mount beim Systemstart

Ergänze in der Datei `/etc/fstab`:

```bash
//CL10NAS/web/ha  /mnt/cl10nas/ha  cifs  credentials=/etc/samba/credentials_cl10nas,iocharset=utf8,file_mode=0777,dir_mode=0777,nofail  0  0
```

Anschließend testen:

```bash
sudo mount -a
```

---

## ✅ Prüfung

```bash
ls /mnt/cl10nas/ha
```

Wenn du die Inhalte der Freigabe siehst, war der Vorgang erfolgreich.

---

## 📌 Hinweise

- Falls `CL10NAS` nicht auflösbar ist, verwende stattdessen die IP-Adresse der NAS, z. B.: `//192.168.2.121/web/ha`
- Prüfe im NAS-Dienstmenü, ob **SMB aktiviert** ist
- Stelle sicher, dass der Benutzer **Zugriffsrechte** auf die Freigabe `web` besitzt




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

#### 💻 Beispielkonfiguration für Ubuntu-Systeme:
```json
{
  "backup_dir": "/mnt/cl10nas/ha",
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
python energy_dashboard.py
```

Die Anwendung ist dann unter `http://127.0.0.1:5000` erreichbar.

Die Funktion `letztes HA-Backup extrahieren und Verbrauchsdaten in InfluxDB schreiben` kann im Energy Dashboard auch über den Button `Lade Sensordaten` ausgelöst werden. Im Projektverzeichnis wird dann die Datei `log_lade_sensordaten.txt` gespeichert, in der die ausgeführten Aktionen und mögliche Fehler protokolliert sind.

---

## 📊 Visualisierung

Die Anwendung verwendet folgende HTML-Vorlagen:

- `drilldown_day.html` – Tagesansicht
- `drilldown_month.html` – Monatsansicht
- `drilldown_year.html` – Jahresansicht
- `total_per_sensor.html` – Gesamtverbrauch der Einzelgeräte

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
├── energy_dashboard.py          # Flask Web-App zur Visualisierung
├── requirements.txt             # Abhängigkeiten
```

---

## 🧩 Lizenz

Dieses Projekt steht unter keiner spezifischen Lizenz. Nutzung auf eigenes Risiko.

---

## 🧑‍💻 Autor

Siegfried Schmidt
