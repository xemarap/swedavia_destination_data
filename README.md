# Swedavia Destination Data

ETL pipeline that transforms Swedavia annual passenger statistics for Stockholm Arlanda Airport (2016–2025) into a geocoded, Tableau-ready CSV.

## Requirements

- Python 3.x
- Packages listed in [requirements.txt](requirements.txt): `pandas`, `openpyxl`, `geopy`, `pycountry-convert`

## Setup

```powershell
# Create and activate a virtual environment (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the three scripts in order from the project root:

```powershell
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

## Output Schema (`visualization_data.csv`)

The `visualization_data.csv` is used for creating the Tableau visualization.

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

## Tableau Workbook

The Tableau workbook (`.twb`) used to visualize this data is not included in this repository. You can find, explore and download the published visualization on my [Tableau Public profile](https://public.tableau.com/app/profile/emanuel.raptis/vizzes)

This is a screenshot of the map visualization filtered for destinations in Europe:

![Number of passengers per destination in 2025, filtered to Europe](images/Europe%20filtered%20map.png)

## Adding New Year Files

Drop `destinationsstatistik_YYYY.xlsx` into `Data/` and re-run all three scripts. If new country name variants appear, add them to `COUNTRY_NORMALIZE` in `Scripts/01_clean_data.py` and re-check `CONTINENT_OVERRIDES` in `Scripts/03_build_viz_dataset.py`.

## Acknowledgements

- Thanks to [Swedavia](https://www.swedavia.se/om-swedavia/statistik/) for publishing their passenger statistics as open data.
- Geocoding is performed using [geopy](https://github.com/geopy/geopy) and the [Nominatim](https://nominatim.org/) service. If you reuse or extend the geocoding step, please follow [Nominatim's usage policy](https://operations.osmfoundation.org/policies/nominatim/).
- Continent lookups are performed using [pycountry-convert](https://pypi.org/project/pycountry-convert/), which maps country names to their continent.

## Disclaimer

This is an independent project and is not associated with or endorsed by Swedavia.
