"""
Joins cleaned passenger data with geocoordinates and adds enrichment columns
(domestic/international flag, continent) to produce a Tableau-ready CSV.

Requires:
  output/cleaned_passenger_data.csv  — from 01_clean_data.py
  output/destination_coordinates.csv — from 02_geocode_destinations.py
"""

from pathlib import Path

import pandas as pd
import pycountry_convert as pc

DATA_DIR = Path(__file__).parent.parent / "Data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CLEANED_FILE = OUTPUT_DIR / "cleaned_passenger_data.csv"
COORDS_FILE = OUTPUT_DIR / "destination_coordinates.csv"
OUTPUT_FILE = OUTPUT_DIR / "visualization_data.csv"
PATH_OUTPUT_FILE = DATA_DIR / "visualization_data_paths.csv"

# Stockholm Arlanda fixed coordinates (used as origin for all routes)
ARLANDA_LAT = 59.6519
ARLANDA_LON = 17.9186

# pycountry_convert continent code → readable name
_CONTINENT_CODE_MAP = {
    "AF": "Africa",
    "AN": "Antarctica",
    "AS": "Asia",
    "EU": "Europe",
    "NA": "Americas",
    "OC": "Oceania",
    "SA": "Americas",
}

# Hard-coded overrides for territories, disputed states, and combined entries
# that pycountry_convert cannot look up by name.
CONTINENT_OVERRIDES: dict[str, str] = {
    # Edge-case countries / territories
    "Kosovo": "Europe",
    "North Macedonia": "Europe",
    "Bosnia and Herzegovina": "Europe",
    "Montenegro": "Europe",
    "Moldova": "Europe",
    "Belarus": "Europe",
    "Gibraltar": "Europe",
    "Cyprus": "Europe",
    # Transcontinental — use conventional assignment for flight context
    "Russia": "Europe",
    "Turkey": "Europe",
    "Azerbaijan": "Europe",
    "Georgia": "Europe",
    "Armenia": "Europe",
    "Kazakhstan": "Asia",
    "Kyrgyzstan": "Asia",
    "Turkmenistan": "Asia",
    "Uzbekistan": "Asia",
    # Asian territories
    "Hong Kong": "Asia",
    "Macau": "Asia",
    "Taiwan": "Asia",
    "South Korea": "Asia",
    "Maldives": "Asia",
    # African islands / territories
    "Cape Verde": "Africa",
    "Seychelles": "Africa",
    "Mauritius": "Africa",
    "Madagascar": "Africa",
    # North/Central American territories and Caribbean islands
    "Puerto Rico": "Americas",
    "Aruba": "Americas",
    "Bermuda": "Americas",
    "Cayman Islands": "Americas",
    "Martinique": "Americas",
    "Guadeloupe": "Americas",
    "French Antilles": "Americas",
    "Netherlands Antilles": "Americas",
    "Turks and Caicos Islands": "Americas",
    "St. Vincent and the Grenadines": "Americas",
    "Antigua and Barbuda": "Americas",
    "Grenada": "Americas",
    "Barbados": "Americas",
    "Jamaica": "Americas",
    "Bahamas": "Americas",
    "Dominican Republic": "Americas",
    "Cuba": "Americas",
    "Trinidad and Tobago": "Americas",
    # Combined / ambiguous entries
    "Sudan/South Sudan": "Africa",
    "Denmark/Greenland": "Europe",
    # Catch-all
    "Unknown": "Unknown",
    "(tom)": "Unknown",
}


def get_continent(country: str) -> str:
    if pd.isna(country):
        return "Unknown"
    if country in CONTINENT_OVERRIDES:
        return CONTINENT_OVERRIDES[country]
    try:
        alpha2 = pc.country_name_to_country_alpha2(country, cn_name_format="default")
        code = pc.country_alpha2_to_continent_code(alpha2)
        return _CONTINENT_CODE_MAP.get(code, "Unknown")
    except Exception:
        return "Unknown"


def build_path_format(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape one-row-per-route into two-rows-per-route for Tableau path marks.

    Each source row becomes path_order=1 (Arlanda) and path_order=2 (destination).
    Rows with null dest coords are kept; Tableau skips them automatically.
    """
    carry_cols = [
        "year", "airport", "country", "city",
        "q1", "q2", "q3", "q4", "total",
        "is_domestic", "route_type", "continent",
    ]

    # Two source rows share the same (year, country, city) for Bangalore 2021 and
    # Milan 2022 — dedup so route_id is unique and each arc is a clean two-point line.
    df_deduped = df.drop_duplicates(subset=["year", "country", "city"]).reset_index(drop=True)

    df_deduped["route_id"] = (
        df_deduped["year"].astype(str)
        + "_"
        + df_deduped["country"].str.replace(" ", "_", regex=False)
        + "_"
        + df_deduped["city"].str.replace(" ", "_", regex=False)
    )

    origins = df_deduped[carry_cols + ["route_id"]].copy()
    origins["path_order"] = 1
    origins["point_lat"] = ARLANDA_LAT
    origins["point_lon"] = ARLANDA_LON

    dests = df_deduped[carry_cols + ["route_id"]].copy()
    dests["path_order"] = 2
    dests["point_lat"] = df_deduped["dest_lat"].values
    dests["point_lon"] = df_deduped["dest_lon"].values

    output_cols = [
        "route_id", "year", "airport", "country", "city",
        "q1", "q2", "q3", "q4", "total",
        "is_domestic", "route_type", "continent",
        "path_order", "point_lat", "point_lon",
    ]
    path_df = (
        pd.concat([origins, dests], ignore_index=True)[output_cols]
        .sort_values(["year", "country", "city", "path_order"])
        .reset_index(drop=True)
    )
    return path_df


def main() -> None:
    for path in (CLEANED_FILE, COORDS_FILE):
        if not path.exists():
            script = "01_clean_data.py" if "cleaned" in path.name else "02_geocode_destinations.py"
            raise FileNotFoundError(f"{path} not found. Run {script} first.")

    cleaned = pd.read_csv(CLEANED_FILE, dtype={"country": str, "city": str})
    coords = pd.read_csv(
        COORDS_FILE, dtype={"country": str, "city": str}
    )[["country", "city", "lat", "lon"]]

    df = cleaned.merge(coords, on=["country", "city"], how="left")
    df = df.rename(columns={"lat": "dest_lat", "lon": "dest_lon"})

    df["origin_airport"] = "Stockholm Arlanda"
    df["origin_lat"] = ARLANDA_LAT
    df["origin_lon"] = ARLANDA_LON

    df["is_domestic"] = df["country"].str.lower() == "sweden"
    df["route_type"] = df["is_domestic"].map({True: "Domestic", False: "International"})

    print("Mapping continents ...")
    df["continent"] = df["country"].apply(get_continent)

    output_cols = [
        "year", "airport", "country", "city",
        "q1", "q2", "q3", "q4", "total",
        "is_domestic", "route_type", "continent",
        "origin_airport", "origin_lat", "origin_lon",
        "dest_lat", "dest_lon",
    ]
    df = df[output_cols]
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig", sep=";")

    print("Building path format for Tableau ...")
    path_df = build_path_format(df)
    path_df.to_csv(PATH_OUTPUT_FILE, index=False, encoding="utf-8-sig", sep=";")
    null_dest = path_df[path_df["path_order"] == 2]["point_lat"].isna().sum()
    print(f"Path rows written  : {len(path_df)}  ({len(path_df) // 2} routes x 2 points)")
    print(f"Null dest coords   : {null_dest} destination points without coords")
    print(f"Path output        : {PATH_OUTPUT_FILE}")

    print(f"\nRows written      : {len(df)}")
    print(f"Missing dest coords: {df['dest_lat'].isna().sum()} rows")
    print(f"Domestic routes   : {df['is_domestic'].sum()}")
    print(f"Output            : {OUTPUT_FILE}")
    print("\nContinent breakdown:")
    print(df["continent"].value_counts().to_string())
    print("\nRoute type breakdown:")
    print(df["route_type"].value_counts().to_string())

    # Warn about Unknown continent entries that are not the expected catch-alls
    unknown = df[df["continent"] == "Unknown"]
    if not unknown.empty:
        unexpected = unknown[~unknown["country"].isin({"Unknown", "(tom)"})]
        if not unexpected.empty:
            print(f"\nWARNING: {len(unexpected)} rows with unexpected 'Unknown' continent:")
            print(unexpected[["country", "city"]].drop_duplicates().to_string(index=False))


if __name__ == "__main__":
    main()
