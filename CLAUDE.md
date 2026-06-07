# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

ETL pipeline that transforms Swedavia annual passenger statistics (Stockholm Arlanda Airport, 2016–2025) into a geocoded, Tableau-ready CSV. The three scripts must be run in order.

## Running the Pipeline

```powershell
# Activate venv (PowerShell)
.\.venv\Scripts\Activate.ps1

# Step 1 — clean and union all Excel files (~30 seconds)
python Scripts/01_clean_data.py

# Step 2 — geocode destinations via Nominatim (~18 minutes on first run, instant on re-run)
python Scripts/02_geocode_destinations.py

# Step 3 — join coordinates and add enrichment columns (~5 seconds)
python Scripts/03_build_viz_dataset.py
```

Script 2 is safe to interrupt and restart — it saves progress every 10 entries to `output/destination_coordinates.csv` and skips already-geocoded pairs on the next run.

## Data Flow

```
Data/destinationsstatistik_YYYY.xlsx    (10 files, 2016–2025)
        ↓  01_clean_data.py
output/cleaned_passenger_data.csv       (3 037 rows, Arlanda only)
        ↓  02_geocode_destinations.py
output/destination_coordinates.csv      (one row per unique country+city pair)
        ↓  03_build_viz_dataset.py
output/visualization_data.csv           (Tableau-ready final output)
```

## Key Architecture Decisions

**Excel structure quirks handled by Script 1:**
- First 9 rows of each file are title/header rows; data starts at row 10 (`skiprows=9`).
- Both `airport` and `country` columns are sparse in 2016–2023 (only the first row of each block is filled); both need `ffill()` before filtering.
- Summa (subtotal) rows always have `city = None` — this single `notna()` filter removes all of them reliably.
- Country names changed from Swedish (2016–2021, e.g. `Sverige`, `Belgien`) to English ALLCAPS (2022–2025, e.g. `SWEDEN`, `BELGIUM`). The `COUNTRY_NORMALIZE` dict in Script 1 maps both forms to clean English. Use `map(lambda x: COUNTRY_NORMALIZE.get(str(x), x))` — not `replace()` — because pandas 3.0 `StringDtype` does not reliably match dict keys with `replace()`.
- Airport name for Arlanda varies by year (`STOCKHOLM-ARLANDA`, `Stockholm Arlanda`, `Stockholm Arlanda Airport`); filter uses `str.contains("arlanda", case=False)`.

**Geocoding (Script 2):**
- Nominatim ToS: 1 request/second max. `RATE_LIMIT_SECONDS = 1.1` is intentionally slightly over 1s.
- Arlanda's coordinates are hardcoded (`59.6519, 17.9186`) and injected directly, not geocoded.
- Ungeocodable placeholders (`(tom)`, `Unknown`, `UTRIKES FLYGPLATS`) are skipped without hitting the API.

**Continent mapping (Script 3):**
- `CONTINENT_OVERRIDES` dict handles ~30 edge cases (territories, disputed states, combined entries like `Sudan/South Sudan`, `Denmark/Greenland`) before falling back to `pycountry_convert`.
- `is_domestic` flag: `country.str.lower() == "sweden"` (post-normalization, Swedish domestic destinations always appear as `"Sweden"`).

## Output Schema (`visualization_data.csv`)

| Column | Description |
|---|---|
| `year` | 2016–2025 |
| `airport` | Always Stockholm Arlanda (various name variants from source) |
| `country` | Destination country (clean English) |
| `city` | Destination city/airport code as in source |
| `q1`–`q4` | Quarterly passengers (NaN if no service that quarter) |
| `total` | Annual passengers on this route |
| `is_domestic` | Boolean — True if country = Sweden |
| `route_type` | `"Domestic"` / `"International"` |
| `continent` | Destination continent |
| `origin_airport` | `"Stockholm Arlanda"` (constant) |
| `origin_lat` / `origin_lon` | `59.6519` / `17.9186` (constant) |
| `dest_lat` / `dest_lon` | Geocoded destination coordinates (NaN for unknown destinations) |

## Adding New Year Files

Drop `destinationsstatistik_YYYY.xlsx` into `Data/` and re-run all three scripts. If new country name variants appear, add them to `COUNTRY_NORMALIZE` in `Scripts/01_clean_data.py` and re-check `CONTINENT_OVERRIDES` in `Scripts/03_build_viz_dataset.py`.
