import sqlite3
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def initialize_database():
    data_folder = BASE_DIR / "pulse_data"
    data_folder.mkdir(exist_ok=True)

    with sqlite3.connect(data_folder / "pulse_history.db") as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS routes (
            route_id TEXT PRIMARY KEY,
            route_name TEXT,
            transit_mode TEXT
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_start TEXT NOT NULL,
            collection_end TEXT NOT NULL,
            total_predictions INTEGER
        );

        CREATE TABLE IF NOT EXISTS predictions (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            prediction_id TEXT NOT NULL,
            route_id TEXT NOT NULL,
            direction_id INTEGER,
            trip_id TEXT,
            stop_id TEXT,
            collected_at TEXT,
            predicted_arrival TEXT,
            predicted_departure TEXT,
            scheduled_arrival TEXT,
            scheduled_departure TEXT,
            arrival_delay_min REAL,
            departure_delay_min REAL,
            FOREIGN KEY (snapshot_id)
                REFERENCES snapshots(snapshot_id),
            FOREIGN KEY (route_id)
                REFERENCES routes(route_id),
            UNIQUE(snapshot_id, prediction_id)
        );

        CREATE INDEX IF NOT EXISTS idx_predictions_route
        ON predictions(route_id);

        CREATE INDEX IF NOT EXISTS idx_predictions_trip
        ON predictions(trip_id);

        CREATE INDEX IF NOT EXISTS idx_predictions_stop
        ON predictions(stop_id);

        CREATE INDEX IF NOT EXISTS idx_predictions_time
        ON predictions(collected_at);

        CREATE INDEX IF NOT EXISTS idx_predictions_snapshot_route
        ON predictions(snapshot_id, route_id);
        """)

        modes = {
            0: "Light Rail",
            1: "Subway",
            2: "Commuter Rail",
            3: "Bus",
            4: "Ferry"
        }

        url = "https://api-v3.mbta.com/routes"
        params = {"page[limit]": 100}
        records = []

        while url:
            response = requests.get(
                url, params=params, timeout=30
            )
            response.raise_for_status()
            payload = response.json()

            for route in payload["data"]:
                attrs = route["attributes"]

                records.append((
                    route["id"],
                    attrs.get("long_name")
                    or attrs.get("short_name")
                    or route["id"],
                    modes.get(attrs.get("type"), "Other")
                ))

            url = (payload.get("links") or {}).get("next")
            params = None

        conn.executemany("""
            INSERT OR IGNORE INTO routes
            (route_id, route_name, transit_mode)
            VALUES (?, ?, ?)
        """, records)

    print("Database initialized successfully.")
    print("Routes retrieved:", len(records))


if __name__ == "__main__":
    initialize_database()
