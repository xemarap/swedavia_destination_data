"""
One-time migration: rename Swedish/non-English city (and country) names in
output/destination_coordinates.csv to match the normalised English names
now produced by 01_clean_data.py.

Safe to re-run (idempotent). Can be deleted after running once.
"""
import importlib.util
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(__file__).parent.parent / "output"
COORDS_FILE = OUTPUT_DIR / "destination_coordinates.csv"

# Import normalisation functions directly from 01_clean_data.py so there is
# a single source of truth — no need to keep a second copy of the dicts here.
_spec = importlib.util.spec_from_file_location(
    "clean_data", Path(__file__).parent / "01_clean_data.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
COUNTRY_NORMALIZE: dict = _mod.COUNTRY_NORMALIZE
_normalize_city = _mod._normalize_city


def main() -> None:
    df = pd.read_csv(COORDS_FILE, encoding="utf-8-sig", dtype=str)
    n_before = len(df)
    print(f"Loaded {n_before} rows from {COORDS_FILE.name}")

    df["country"] = df["country"].map(lambda x: COUNTRY_NORMALIZE.get(str(x), x))
    df["city"] = df["city"].map(_normalize_city)

    # Renaming can create duplicate (country, city) pairs (e.g. NEAPEL + Neapel
    # both become Naples). Keep the row that has valid coordinates; if both have
    # coords, keep the first.
    df["_has_coords"] = df["lat"].notna().astype(int)
    df = (
        df.sort_values("_has_coords", ascending=False)
        .drop_duplicates(subset=["country", "city"], keep="first")
        .drop(columns=["_has_coords"])
        .reset_index(drop=True)
    )

    n_after = len(df)
    print(f"After normalisation + dedup: {n_after} rows  ({n_before - n_after} duplicates removed)")

    df.to_csv(COORDS_FILE, index=False, encoding="utf-8-sig")
    print(f"Saved to {COORDS_FILE}\n")

    checks = [
        ("Belgium", "Brussels"), ("Greece", "Athens"), ("Italy", "Rome"),
        ("Austria", "Vienna"), ("Denmark", "Copenhagen"), ("Switzerland", "Zurich"),
        ("Poland", "Warsaw"), ("Romania", "Bucharest"), ("Serbia", "Belgrade"),
        ("Portugal", "Lisbon"), ("Spain", "Tenerife"), ("Italy", "Naples"),
        ("Finland", "Helsinki"), ("Finland", "Tampere"), ("Finland", "Vaasa"),
        ("Finland", "Turku"),
    ]
    print("Spot-check:")
    for country, city in checks:
        row = df[(df["country"] == country) & (df["city"] == city)]
        if not row.empty:
            lat, lon = row.iloc[0]["lat"], row.iloc[0]["lon"]
            print(f"  {city}, {country}: ({lat}, {lon}) OK")
        else:
            print(f"  {city}, {country}: NOT FOUND")


if __name__ == "__main__":
    main()
