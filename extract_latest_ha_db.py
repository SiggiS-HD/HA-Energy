import tarfile
import os
from pathlib import Path
import shutil
import json
from datetime import datetime
import platform

def load_config():
    with open(Path(__file__).parent / "config.json", "r") as f:
        return json.load(f)

def extract_latest_ha_db():
    config = load_config()

    system = platform.system()
    if system == "Windows":
        backup_dir = Path(config["backup_dir_windows"])
    else:
        backup_dir = Path(config["backup_dir_linux"])

    output_dir = Path(__file__).parent / config["sqlite_dir"]
    temp_dir = output_dir / "temp_extract"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        final_path = output_dir / "home-assistant_v2.db"

        if final_path.exists():
            modified_date = datetime.fromtimestamp(final_path.stat().st_mtime).strftime("%Y-%m-%d")
            if modified_date == today:
                print(f"[Info] Die Datei home-assistant_v2.db wurde heute ({today}) bereits extrahiert. Vorgang wird übersprungen.")
                return str(final_path)

        backups = sorted(backup_dir.glob("*.tar"), key=os.path.getmtime, reverse=True)
        if not backups:
            print("[Info] Kein Backup gefunden in", backup_dir)
            return None

        latest_backup = backups[0]
        print(f"[Backup] Letztes Backup gefunden: {latest_backup.name}")

        with tarfile.open(latest_backup, "r") as tar:
            tar.extractall(path=temp_dir)

        inner_tar_path = temp_dir / "homeassistant.tar.gz"
        if not inner_tar_path.exists():
            print("[Info] Datei homeassistant.tar.gz nicht im Backup gefunden.")
            return None

        with tarfile.open(inner_tar_path, "r") as inner_tar:
            inner_tar.extractall(path=temp_dir)

        db_path = next(temp_dir.rglob("home-assistant_v2.db"), None)
        if not db_path:
            print("[Info] Datei home-assistant_v2.db nicht gefunden.")
            return None

        shutil.copy(db_path, final_path)
        print(f"[OK] Datenbank erfolgreich extrahiert nach: {final_path}")

        shutil.rmtree(temp_dir)
        return str(final_path)

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    extract_latest_ha_db()
