
import requests
import pandas as pd
import sqlite3
import time
import os

from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

data_folder = Path("pulse_data")

conn = sqlite3.connect(
    data_folder / "pulse_history.db",
    timeout=60
)

conn.execute("PRAGMA foreign_keys = ON")

df_network_routes = pd.read_sql_query(
    "SELECT route_id, route_name, transit_mode FROM routes",
    conn
)

def get_pulse_batch(route_ids):

    url = "https://api-v3.mbta.com/predictions"

    params = {
        "filter[route]": ",".join(route_ids),
        "include": "schedule",
        "page[limit]": 100
    }

    all_predictions = []
    schedules = {}
    pages = 0

    collected_at = pd.Timestamp.now(
        tz="America/New_York"
    )

    # Retrieve all prediction pages
    while url is not None:

        # Handle API rate limits
        for attempt in range(5):

            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After", ""
                )

                wait_time = (
                    int(retry_after)
                    if retry_after.isdigit()
                    else 5 * (2 ** attempt)
                )

                print(
                    f"Rate limit reached. "
                    f"Waiting {wait_time} seconds."
                )

                time.sleep(wait_time)

            else:
                break

        response.raise_for_status()

        payload = response.json()

        all_predictions.extend(
            payload.get("data", [])
        )

        # Store associated schedules
        for item in payload.get("included", []):

            if item["type"] == "schedule":

                schedules[item["id"]] = (
                    item["attributes"]
                )

        pages += 1

        url = (
            payload.get("links") or {}
        ).get("next")

        params = None

        time.sleep(0.5)

    # Process prediction records
    records = []

    for prediction in all_predictions:

        attrs = prediction["attributes"]
        rels = prediction["relationships"]

        def relationship_id(name):

            return (
                rels.get(name, {}).get("data") or {}
            ).get("id")

        schedule_id = relationship_id("schedule")

        schedule = schedules.get(schedule_id, {})

        records.append({

            "prediction_id": prediction["id"],
            "route_id": relationship_id("route"),
            "direction_id": attrs.get("direction_id"),
            "trip_id": relationship_id("trip"),
            "stop_id": relationship_id("stop"),
            "collected_at": collected_at,

            "predicted_arrival": attrs.get(
                "arrival_time"
            ),

            "predicted_departure": attrs.get(
                "departure_time"
            ),

            "scheduled_arrival": schedule.get(
                "arrival_time"
            ),

            "scheduled_departure": schedule.get(
                "departure_time"
            )
        })

    df = pd.DataFrame(records)

    # Handle empty responses
    if df.empty:

        print("No predictions available.")

        return df

    # Remove duplicate predictions
    df = df.drop_duplicates(
        subset=["prediction_id"],
        keep="last"
    ).copy()

    # Convert timestamps
    time_columns = [
        "predicted_arrival",
        "predicted_departure",
        "scheduled_arrival",
        "scheduled_departure"
    ]

    for column in time_columns:

        df[column] = pd.to_datetime(
            df[column],
            utc=True,
            errors="coerce"
        )

    # Calculate schedule deviations
    df["arrival_delay_min"] = (
        df["predicted_arrival"]
        - df["scheduled_arrival"]
    ).dt.total_seconds() / 60

    df["departure_delay_min"] = (
        df["predicted_departure"]
        - df["scheduled_departure"]
    ).dt.total_seconds() / 60

    print("\nBatch collection complete")
    print("Snapshot collected:", collected_at)
    print("Pages retrieved:", pages)
    print("Routes requested:", len(route_ids))
    print("Routes returned:", df["route_id"].nunique())
    print("Raw predictions:", len(all_predictions))
    print("Unique predictions:", len(df))
    print("Unique schedules:", len(schedules))

    return df


def collect_pulse_network(batch_size=10):

    all_routes = df_network_routes["route_id"].tolist()

    collected_frames = []
    failed_batches = []

    total_batches = (
        len(all_routes) + batch_size - 1
    ) // batch_size

    collection_start = pd.Timestamp.now(
        tz="America/New_York"
    )

    print("Starting PULSE network collection")
    print("Total routes:", len(all_routes))
    print("Total batches:", total_batches)

    for i in range(0, len(all_routes), batch_size):

        batch = all_routes[i:i + batch_size]

        batch_number = i // batch_size + 1

        print(
            f"\nProcessing batch "
            f"{batch_number}/{total_batches}"
        )

        try:

            df_batch = get_pulse_batch(batch)

            if not df_batch.empty:

                collected_frames.append(df_batch)

        except Exception as error:

            failed_batches.append(batch)

            print("Batch failed:", error)

        time.sleep(3)

    if not collected_frames:

        print("No predictions collected.")

        return pd.DataFrame(), failed_batches

    df_network = pd.concat(
        collected_frames,
        ignore_index=True
    )

    df_network = df_network.drop_duplicates(
        subset=["prediction_id"],
        keep="last"
    ).copy()

    df_network = df_network.merge(
        df_network_routes,
        on="route_id",
        how="left",
        validate="many_to_one"
    )

    collection_end = pd.Timestamp.now(
        tz="America/New_York"
    )

    print("\nPULSE COLLECTION COMPLETE")
    print("-" * 40)

    print("Total predictions:", len(df_network))

    print(
        "Unique routes:",
        df_network["route_id"].nunique()
    )

    print("Failed batches:", len(failed_batches))

    print(
        "Collection duration:",
        collection_end - collection_start
    )

    return df_network, failed_batches


def save_pulse_snapshot(df_network):

    if df_network.empty:
        print("No predictions available to save.")
        return None

    df_db = df_network.copy()

    time_columns = [
        "collected_at",
        "predicted_arrival",
        "predicted_departure",
        "scheduled_arrival",
        "scheduled_departure"
    ]

    for column in time_columns:

        df_db[column] = pd.to_datetime(
            df_db[column],
            utc=True,
            errors="coerce"
        ).dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    if df_db["collected_at"].isna().any():
        raise ValueError("Missing collection timestamps.")

    collection_start = df_db["collected_at"].min()
    collection_end = df_db["collected_at"].max()

    prediction_columns = [
        "prediction_id",
        "route_id",
        "direction_id",
        "trip_id",
        "stop_id",
        "collected_at",
        "predicted_arrival",
        "predicted_departure",
        "scheduled_arrival",
        "scheduled_departure",
        "arrival_delay_min",
        "departure_delay_min"
    ]

    df_insert = df_db[prediction_columns].astype(object)

    df_insert = df_insert.where(
        pd.notna(df_insert),
        None
    )

    with conn:

        existing = conn.execute(
            """
            SELECT snapshot_id
            FROM snapshots
            WHERE collection_start = ?
              AND collection_end = ?
            """,
            (collection_start, collection_end)
        ).fetchone()

        if existing:

            print("Snapshot already exists.")
            print("Snapshot ID:", existing[0])

            return existing[0]

        cursor = conn.execute(
            """
            INSERT INTO snapshots (
                collection_start,
                collection_end,
                total_predictions
            )
            VALUES (?, ?, ?)
            """,
            (
                collection_start,
                collection_end,
                len(df_db)
            )
        )

        new_snapshot_id = cursor.lastrowid

        prediction_records = [
            (new_snapshot_id, *row)
            for row in df_insert.itertuples(
                index=False,
                name=None
            )
        ]

        conn.executemany(
            """
            INSERT INTO predictions (
                snapshot_id,
                prediction_id,
                route_id,
                direction_id,
                trip_id,
                stop_id,
                collected_at,
                predicted_arrival,
                predicted_departure,
                scheduled_arrival,
                scheduled_departure,
                arrival_delay_min,
                departure_delay_min
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            prediction_records
        )

    print("Snapshot successfully stored!")
    print("Snapshot ID:", new_snapshot_id)
    print("Predictions stored:", len(df_db))

    return new_snapshot_id


def run_pulse_pipeline(batch_size=10):

    print("=" * 50)
    print("PROJECT PULSE - NETWORK DATA PIPELINE")
    print("=" * 50)

    # 1. Collect network predictions

    df_network, failed_batches = collect_pulse_network(
        batch_size=batch_size
    )

    if df_network.empty:
        print("Pipeline stopped: No data collected.")
        return None

    # 2. Validate collected data

    print("\nValidating collected data...")

    duplicate_count = df_network[
        "prediction_id"
    ].duplicated().sum()

    missing_modes = df_network[
        "transit_mode"
    ].isna().sum()

    if duplicate_count > 0 or missing_modes > 0:
        print("Pipeline stopped: Data validation failed.")
        return None

    total_routes = df_network_routes["route_id"].nunique()

    collected_routes = df_network["route_id"].nunique()

    coverage = collected_routes / total_routes * 100

    # 3. Save CSV backup

    data_folder = Path("pulse_data")
    data_folder.mkdir(exist_ok=True)

    timestamp = pd.Timestamp.now(
        tz="America/New_York"
    ).strftime("%Y%m%d_%H%M%S_%f")

    backup_path = (
        data_folder / f"pulse_network_{timestamp}.csv"
    )

    df_network.to_csv(backup_path, index=False)

    print("CSV backup saved:", backup_path)

    # 4. Check for collection failures

    if failed_batches:
        print("Pipeline stopped: Some batches failed.")
        print("Failed batches:", failed_batches)
        print("Partial collection preserved in CSV.")
        return None

    # 5. Store historical snapshot

    new_snapshot_id = save_pulse_snapshot(df_network)

    # 6. Display pipeline summary

    print("\nPULSE PIPELINE SUMMARY")
    print("-" * 40)

    print("Snapshot ID:", new_snapshot_id)
    print("Total predictions:", len(df_network))
    print("Routes collected:", collected_routes)
    print("Network coverage:", round(coverage, 2), "%")
    print("Duplicate predictions:", duplicate_count)
    print("Missing classifications:", missing_modes)
    print("Failed batches:", len(failed_batches))

    print("\nPredictions by transportation mode:")
    print(df_network["transit_mode"].value_counts())

    print("\nPipeline completed successfully!")

    return new_snapshot_id



if __name__ == "__main__":
    try:
        snapshot_id = run_pulse_pipeline(batch_size=10)

        if snapshot_id is None:
            raise SystemExit(1)

    finally:
        conn.close()
