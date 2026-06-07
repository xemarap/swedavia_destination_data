"""
Geocodes unique (country, city) destination pairs from cleaned passenger data.

Run once — results are stored in output/destination_coordinates.csv and reused
on subsequent runs (only new pairs are geocoded). Safe to interrupt and restart.

Nominatim usage policy: max 1 request/second, requires a descriptive user-agent.
"""

import time
from pathlib import Path

import pandas as pd
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

DATA_DIR = Path(__file__).parent.parent / "Data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
CLEANED_FILE = OUTPUT_DIR / "cleaned_passenger_data.csv"
COORDS_FILE = OUTPUT_DIR / "destination_coordinates.csv"

# Nominatim ToS: max 1 request/second. Using 1.1s to avoid edge-case violations.
RATE_LIMIT_SECONDS = 1.1
SAVE_EVERY = 10  # Write progress to disk every N geocoded entries

# Values that cannot be meaningfully geocoded — skip without hitting the API
UNGEOCODABLE = {"(tom)", "Unknown", "UTRIKES FLYGPLATS", "UNKNOWN", ""}

# Stockholm Arlanda — added as the origin point
ARLANDA_PAIR = ("Sweden", "Stockholm Arlanda")
ARLANDA_LAT = 59.6519
ARLANDA_LON = 17.9186


def load_existing() -> tuple[pd.DataFrame, set[tuple[str, str]]]:
    if COORDS_FILE.exists():
        df = pd.read_csv(COORDS_FILE, dtype={"country": str, "city": str})
        done = set(zip(df["country"], df["city"]))
        return df, done
    empty = pd.DataFrame(
        columns=["country", "city", "lat", "lon", "geocode_query", "geocode_status"]
    )
    return empty, set()


def save_progress(existing_df: pd.DataFrame, new_rows: list[dict]) -> None:
    if not new_rows:
        return
    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined.to_csv(COORDS_FILE, index=False, encoding="utf-8-sig")


def geocode_one(
    geolocator: Nominatim, country: str, city: str
) -> tuple[float | None, float | None, str, str]:
    """Returns (lat, lon, query_used, status)."""

    if country in UNGEOCODABLE or city in UNGEOCODABLE:
        return None, None, "skipped", "ungeocodable"

    # Primary: "City, Country"
    query = f"{city}, {country}"
    try:
        loc = geolocator.geocode(query, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, query, "ok_primary"
    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        print(f"  Warning: {exc} — '{query}'")

    time.sleep(RATE_LIMIT_SECONDS)

    # Fallback: country name only
    try:
        loc = geolocator.geocode(country, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, country, "ok_fallback"
    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        print(f"  Warning (fallback): {exc} — '{country}'")

    return None, None, query, "failed"


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not CLEANED_FILE.exists():
        raise FileNotFoundError(
            f"{CLEANED_FILE} not found. Run 01_clean_data.py first."
        )

    cleaned = pd.read_csv(CLEANED_FILE, dtype={"country": str, "city": str})
    pairs: set[tuple[str, str]] = set(zip(cleaned["country"], cleaned["city"]))
    pairs.add(ARLANDA_PAIR)

    existing_df, done = load_existing()

    # Arlanda itself: inject with known coordinates if not already present
    if ARLANDA_PAIR not in done:
        arlanda_row = pd.DataFrame(
            [
                {
                    "country": ARLANDA_PAIR[0],
                    "city": ARLANDA_PAIR[1],
                    "lat": ARLANDA_LAT,
                    "lon": ARLANDA_LON,
                    "geocode_query": "hardcoded",
                    "geocode_status": "hardcoded",
                }
            ]
        )
        existing_df = pd.concat([existing_df, arlanda_row], ignore_index=True)
        done.add(ARLANDA_PAIR)
        existing_df.to_csv(COORDS_FILE, index=False, encoding="utf-8-sig")

    to_do = sorted(pairs - done)
    print(f"Total unique pairs : {len(pairs)}")
    print(f"Already geocoded   : {len(done)}")
    print(f"To geocode         : {len(to_do)}")

    if not to_do:
        print("Nothing to do — all pairs already geocoded.")
        _print_summary(existing_df)
        return

    est_minutes = len(to_do) * RATE_LIMIT_SECONDS / 60
    print(f"Estimated time     : ~{est_minutes:.0f} minutes\n")

    geolocator = Nominatim(user_agent="swedavia_passenger_viz")
    new_rows: list[dict] = []

    for i, (country, city) in enumerate(to_do):
        print(f"[{i + 1:4d}/{len(to_do)}] {city}, {country}", end=" ... ", flush=True)
        lat, lon, query, status = geocode_one(geolocator, country, city)
        print(status)

        new_rows.append(
            {
                "country": country,
                "city": city,
                "lat": lat,
                "lon": lon,
                "geocode_query": query,
                "geocode_status": status,
            }
        )

        time.sleep(RATE_LIMIT_SECONDS)

        # Save progress periodically so an interrupted run loses at most SAVE_EVERY entries
        if (i + 1) % SAVE_EVERY == 0:
            save_progress(existing_df, new_rows)
            existing_df = pd.read_csv(COORDS_FILE, dtype={"country": str, "city": str})
            new_rows = []
            print(f"  [Progress saved — {i + 1} new entries written]")

    # Final save
    save_progress(existing_df, new_rows)
    final_df = pd.read_csv(COORDS_FILE, dtype={"country": str, "city": str})
    print(f"\nSaved {len(final_df)} total records to {COORDS_FILE}")
    _print_summary(final_df)


def _print_summary(df: pd.DataFrame) -> None:
    print("\nGeocode status breakdown:")
    print(df["geocode_status"].value_counts().to_string())
    failed = df[df["geocode_status"] == "failed"]
    if not failed.empty:
        print(f"\n{len(failed)} entries could not be geocoded:")
        print(failed[["country", "city", "geocode_query"]].to_string(index=False))


if __name__ == "__main__":
    main()
