
import tarfile
import os
from pathlib import Path
import shutil
import json

def load_config():
    with open(Path(__file__).parent / "config.json", "r") as f:
        return json.load(f)

def extract_latest_ha_db():
    config = load_config()
    backup_dir = Path(config["backup_dir"])
    output_dir = Path(__file__).parent / config["sqlite_dir"]
    temp_dir = output_dir / "temp_extract"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    backups = sorted(backup_dir.glob("*.tar"), key=os.path.getmtime, reverse=True)
    if not backups:
        print("❌ Kein Backup gefunden in", backup_dir)
        return None

    latest_backup = backups[0]
    print(f"📦 Letztes Backup gefunden: {latest_backup.name}")

    with tarfile.open(latest_backup, "r") as tar:
        tar.extractall(path=temp_dir)

    inner_tar_path = temp_dir / "homeassistant.tar.gz"
    if not inner_tar_path.exists():
        print("❌ Datei homeassistant.tar.gz nicht im Backup gefunden.")
        return None

    with tarfile.open(inner_tar_path, "r") as inner_tar:
        inner_tar.extractall(path=temp_dir)

    db_path = next(temp_dir.rglob("home-assistant_v2.db"), None)
    if not db_path:
        print("❌ Datei home-assistant_v2.db nicht gefunden.")
        return None

    final_path = output_dir / "home-assistant_v2.db"
    shutil.copy(db_path, final_path)
    print(f"✅ Datenbank erfolgreich extrahiert nach: {final_path}")

    shutil.rmtree(temp_dir)
    return str(final_path)

if __name__ == "__main__":
    extract_latest_ha_db()
