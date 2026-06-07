import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "Data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "cleaned_passenger_data.csv"
EXCEL_FILES = sorted(DATA_DIR.glob("destinationsstatistik_*.xlsx"))
COLS = ["airport", "country", "city", "q1", "q2", "q3", "q4", "total"]

# Maps both Swedish names (2016–2021) and English ALLCAPS (2022–2025) to clean English.
# Values not present pass through unchanged (e.g. Finland, Malta, Japan are identical).
COUNTRY_NORMALIZE = {
    # Swedish → English
    "Sverige": "Sweden",
    "Danmark": "Denmark",
    "Norge": "Norway",
    "Island": "Iceland",
    "Spanien": "Spain",
    "Frankrike": "France",
    "Belgien": "Belgium",
    "Nederländerna": "Netherlands",
    "Luxemburg": "Luxembourg",
    "Italien": "Italy",
    "Schweiz": "Switzerland",
    "Österrike": "Austria",
    "Tyskland": "Germany",
    "Polen": "Poland",
    "Tjeckien": "Czech Republic",
    "Slovakien": "Slovakia",
    "Slovenien": "Slovenia",
    "Kroatien": "Croatia",
    "Ungern": "Hungary",
    "Rumänien": "Romania",
    "Bulgarien": "Bulgaria",
    "Estland": "Estonia",
    "Lettland": "Latvia",
    "Litauen": "Lithuania",
    "Albanien": "Albania",
    "Serbien": "Serbia",
    "Makedonien": "North Macedonia",
    "Nordmakedonien": "North Macedonia",
    "Bosnien-Herzegovina": "Bosnia and Herzegovina",
    "Moldavien": "Moldova",
    "Ukraina": "Ukraine",
    "Vitryssland": "Belarus",
    "Ryssland": "Russia",
    "Georgien": "Georgia",
    "Armenien": "Armenia",
    "Azerbajdzjan": "Azerbaijan",
    "Kazakstan": "Kazakhstan",
    "Kirgizistan": "Kyrgyzstan",
    "Turkiet": "Turkey",
    "Cypern": "Cyprus",
    "Grekland": "Greece",
    "Libanon": "Lebanon",
    "Jordanien": "Jordan",
    "Egypten": "Egypt",
    "Marocko": "Morocco",
    "Tunisien": "Tunisia",
    "Algeriet": "Algeria",
    "Saudi Arabien": "Saudi Arabia",
    "Förenade Arabemiraten": "United Arab Emirates",
    "Irak": "Iraq",
    "Indien": "India",
    "Kina": "China",
    "Hong Kong, Kina": "Hong Kong",
    "Macau, Kina": "Macau",
    "Korea, Syd": "South Korea",
    "Maldiverna": "Maldives",
    "Mongoliet": "Mongolia",
    "Kap Verdeöarna": "Cape Verde",
    "Sydafrika": "South Africa",
    "Etiopien": "Ethiopia",
    "Seychellerna": "Seychelles",
    "Brasilien": "Brazil",
    "Antigua och Barbuda": "Antigua and Barbuda",
    "Dominikanska rep": "Dominican Republic",
    "Kuba": "Cuba",
    "NL Antillerna": "Netherlands Antilles",
    "Franska Antillerna": "French Antilles",
    "Gibraltar Storbr": "Gibraltar",
    "Gibraltar Stor": "Gibraltar",
    "Storbritannien": "United Kingdom",
    "Irland": "Ireland",
    "Utrikes land (okänt)": "Unknown",
    "Sudan/Syd Sudan": "Sudan/South Sudan",
    "Danmark/Grönland": "Denmark/Greenland",
    "St Vincent m fl": "St. Vincent and the Grenadines",
    "Turks and Caicos isl": "Turks and Caicos Islands",
    "Kyrgyzsta": "Kyrgyzstan",           # truncated source variant
    "Nl Antillerna": "Netherlands Antilles",  # case variant of NL Antillerna
    "USA": "United States",
    # ALLCAPS English → clean English
    "SWEDEN": "Sweden",
    "DENMARK": "Denmark",
    "NORWAY": "Norway",
    "FINLAND": "Finland",
    "ICELAND": "Iceland",
    "SPAIN": "Spain",
    "FRANCE": "France",
    "BELGIUM": "Belgium",
    "NETHERLANDS": "Netherlands",
    "LUXEMBOURG": "Luxembourg",
    "PORTUGAL": "Portugal",
    "ITALY": "Italy",
    "SWITZERLAND": "Switzerland",
    "AUSTRIA": "Austria",
    "GERMANY": "Germany",
    "POLAND": "Poland",
    "CZECHIA": "Czech Republic",
    "CZECH REPUBLIC": "Czech Republic",
    "SLOVAKIA": "Slovakia",
    "SLOVENIA": "Slovenia",
    "CROATIA": "Croatia",
    "HUNGARY": "Hungary",
    "ROMANIA": "Romania",
    "BULGARIA": "Bulgaria",
    "ESTONIA": "Estonia",
    "LATVIA": "Latvia",
    "LITHUANIA": "Lithuania",
    "ALBANIA": "Albania",
    "SERBIA": "Serbia",
    "MONTENEGRO": "Montenegro",
    "KOSOVO": "Kosovo",
    "NORTH MACEDONIA": "North Macedonia",
    "BOSNIA AND HERZEGOVINA": "Bosnia and Herzegovina",
    "MOLDOVA": "Moldova",
    "UKRAINE": "Ukraine",
    "BELARUS": "Belarus",
    "RUSSIA": "Russia",
    "GEORGIA": "Georgia",
    "ARMENIA": "Armenia",
    "AZERBAIJAN": "Azerbaijan",
    "TURKMENISTAN": "Turkmenistan",
    "KAZAKHSTAN": "Kazakhstan",
    "KYRGYZSTAN": "Kyrgyzstan",
    "UZBEKISTAN": "Uzbekistan",
    "TURKEY": "Turkey",
    "CYPRUS": "Cyprus",
    "MALTA": "Malta",
    "GREECE": "Greece",
    "ISRAEL": "Israel",
    "LEBANON": "Lebanon",
    "JORDAN": "Jordan",
    "EGYPT": "Egypt",
    "MOROCCO": "Morocco",
    "TUNISIA": "Tunisia",
    "ALGERIA": "Algeria",
    "SAUDI ARABIA": "Saudi Arabia",
    "UNITED ARAB EMIRATES": "United Arab Emirates",
    "QATAR": "Qatar",
    "KUWAIT": "Kuwait",
    "BAHRAIN": "Bahrain",
    "IRAQ": "Iraq",
    "IRAN": "Iran",
    "PAKISTAN": "Pakistan",
    "INDIA": "India",
    "CHINA": "China",
    "HONG KONG": "Hong Kong",
    "MACAU": "Macau",
    "JAPAN": "Japan",
    "SOUTH KOREA": "South Korea",
    "TAIWAN": "Taiwan",
    "MALAYSIA": "Malaysia",
    "SINGAPORE": "Singapore",
    "THAILAND": "Thailand",
    "VIETNAM": "Vietnam",
    "AFGHANISTAN": "Afghanistan",
    "SRI LANKA": "Sri Lanka",
    "MALDIVES": "Maldives",
    "MONGOLIA": "Mongolia",
    "CAPE VERDE": "Cape Verde",
    "NIGERIA": "Nigeria",
    "KENYA": "Kenya",
    "TANZANIA": "Tanzania",
    "SOUTH AFRICA": "South Africa",
    "ETHIOPIA": "Ethiopia",
    "GAMBIA": "Gambia",
    "MALI": "Mali",
    "UGANDA": "Uganda",
    "BOTSWANA": "Botswana",
    "MAURITIUS": "Mauritius",
    "SEYCHELLES": "Seychelles",
    "MADAGASCAR": "Madagascar",
    "GHANA": "Ghana",
    "SENEGAL": "Senegal",
    "ANGOLA": "Angola",
    "ZAMBIA": "Zambia",
    "ZIMBABWE": "Zimbabwe",
    "MOZAMBIQUE": "Mozambique",
    "NAMIBIA": "Namibia",
    "CONGO": "Congo",
    "RWANDA": "Rwanda",
    "DJIBOUTI": "Djibouti",
    "SOMALIA": "Somalia",
    "ERITREA": "Eritrea",
    "LIBYA": "Libya",
    "UNITED STATES": "United States",
    "UNITED STATES OF AMERICA": "United States",
    "GREAT BRITAIN": "United Kingdom",
    "IRISH REPUBLIC": "Ireland",
    "BOSNIA-HERZEGOVINA": "Bosnia and Herzegovina",
    "TAJIKISTAN": "Tajikistan",
    "KAZAKSTAN": "Kazakhstan",
    "MACEDONIA": "North Macedonia",
    "CANADA": "Canada",
    "MEXICO": "Mexico",
    "JAMAICA": "Jamaica",
    "BARBADOS": "Barbados",
    "BAHAMAS": "Bahamas",
    "ANTIGUA AND BARBUDA": "Antigua and Barbuda",
    "DOMINICAN REPUBLIC": "Dominican Republic",
    "PUERTO RICO": "Puerto Rico",
    "CUBA": "Cuba",
    "ARUBA": "Aruba",
    "NETHERLANDS ANTILLES": "Netherlands Antilles",
    "BERMUDA": "Bermuda",
    "BRAZIL": "Brazil",
    "ECUADOR": "Ecuador",
    "PERU": "Peru",
    "NICARAGUA": "Nicaragua",
    "COLOMBIA": "Colombia",
    "CHILE": "Chile",
    "ARGENTINA": "Argentina",
    "VENEZUELA": "Venezuela",
    "SURINAME": "Suriname",
    "GUYANA": "Guyana",
    "BOLIVIA": "Bolivia",
    "PARAGUAY": "Paraguay",
    "URUGUAY": "Uruguay",
    "TRINIDAD AND TOBAGO": "Trinidad and Tobago",
    "CAYMAN ISLANDS": "Cayman Islands",
    "MARTINIQUE": "Martinique",
    "GUADELOUPE": "Guadeloupe",
    "FRENCH ANTILLES": "French Antilles",
    "GRENADA": "Grenada",
    "ST. VINCENT AND THE GRENADINES": "St. Vincent and the Grenadines",
    "TURKS AND CAICOS ISLANDS": "Turks and Caicos Islands",
    "TURKS AND CAICOS ISL": "Turks and Caicos Islands",
    "AUSTRALIA": "Australia",
    "NEW ZEALAND": "New Zealand",
    "FIJI": "Fiji",
    "INDONESIA": "Indonesia",
    "PHILIPPINES": "Philippines",
    "CAMBODIA": "Cambodia",
    "MYANMAR": "Myanmar",
    "NEPAL": "Nepal",
    "BANGLADESH": "Bangladesh",
    "OMAN": "Oman",
    "GIBRALTAR": "Gibraltar",
    "UNITED KINGDOM": "United Kingdom",
    "IRELAND": "Ireland",
    "SUDAN/SOUTH SUDAN": "Sudan/South Sudan",
    "DENMARK/GREENLAND": "Denmark/Greenland",
    "UTRIKES FLYGPLATS": "Unknown",
    "UNKNOWN": "Unknown",
}

# Maps city name forms to consistent English names (or Swedish for domestic routes).
# Keys are Title Case because _normalize_city() applies str.title() before the lookup.
# Swedish domestic city names (Göteborg, Malmö, …) are not in this dict — they pass
# through title-cased, preserving Swedish spelling as intended.
CITY_NORMALIZE = {
    # Swedish / other-language city names → English
    "Aten": "Athens",
    "Antwerpen": "Antwerp",
    "Bagdad": "Baghdad",
    "Belgrad": "Belgrade",
    "Bryssel": "Brussels",
    "Bukarest": "Bucharest",
    "Dehli": "Delhi",
    "Firenze": "Florence",
    "Geneve": "Geneva",
    "Genua": "Genoa",
    "Helsingfors": "Helsinki",
    "Kairo": "Cairo",
    "Korfu": "Corfu",
    "Köpenhamn": "Copenhagen",
    "Lissabon": "Lisbon",
    "Milano": "Milan",
    "Moskva": "Moscow",
    "Neapel": "Naples",
    "Prag": "Prague",
    "Rhodos": "Rhodes",
    "Rom": "Rome",
    "Tammerfors": "Tampere",
    "Teheran": "Tehran",
    "Teneriffa": "Tenerife",
    "Vasa": "Vaasa",
    "Venedig": "Venice",
    "Warszawa": "Warsaw",
    "Wien": "Vienna",
    "Åbo": "Turku",
    "Zürich": "Zurich",
}


def _normalize_city(raw: str) -> str:
    """Title-case a city name and translate non-English names to English."""
    city = raw.strip()
    city = city.title()
    # Fix str.title() apostrophe bug: "St. John'S" → "St. John's"
    city = re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), city)
    return CITY_NORMALIZE.get(city, city)


def extract_year(path: Path) -> int:
    return int(re.search(r"(\d{4})", path.stem).group(1))


def read_year(filepath: Path) -> pd.DataFrame:
    year = extract_year(filepath)

    df = pd.read_excel(
        filepath,
        sheet_name=0,
        skiprows=9,
        header=None,
        names=COLS,
        dtype={"airport": str, "country": str, "city": str},
        engine="openpyxl",
    )

    # Drop fully empty rows (trailing blank rows present in some files)
    df = df.dropna(how="all")

    # Forward-fill sparse airport and country columns (2016–2023 only fills first row per block)
    df["airport"] = df["airport"].ffill()
    df["country"] = df["country"].ffill()

    # Strip whitespace from string columns
    for col in ("airport", "country", "city"):
        df[col] = df[col].str.strip()

    # City is always None on every Summa/Totalsumma row — this single filter removes them all
    df = df[df["city"].notna()]

    # Belt-and-suspenders: drop any row where country still contains 'Summa'
    df = df[~df["country"].str.endswith("Summa", na=False)]

    # Filter to Stockholm Arlanda only
    df = df[df["airport"].str.contains("arlanda", case=False, na=False)]

    # Normalize country names to clean English.
    # Using map+lambda instead of replace() because pandas 3.0 StringDtype
    # does not reliably match dict keys with replace().
    df["country"] = df["country"].map(lambda x: COUNTRY_NORMALIZE.get(str(x), x))

    # Normalize city names: consistent Title Case + English translations for
    # Swedish/other-language names used in 2016–2021 (and some later) source files.
    df["city"] = df["city"].map(_normalize_city)

    # Coerce passenger columns to numeric (some cells may be dashes or empty)
    for col in ("q1", "q2", "q3", "q4", "total"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["year"] = year
    return df


def main() -> None:
    if not EXCEL_FILES:
        raise FileNotFoundError(f"No Excel files found in {DATA_DIR}")

    frames = []
    for f in EXCEL_FILES:
        print(f"Reading {f.name} ...", end=" ", flush=True)
        df = read_year(f)
        print(f"{len(df)} rows")
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\nTotal rows: {len(combined)}")
    print(f"Years:      {sorted(combined['year'].unique())}")
    print(f"Output:     {OUTPUT_FILE}")

    # Spot-check for leftover Summa values
    summa_rows = combined[combined["country"].str.contains("Summa", na=False)]
    if not summa_rows.empty:
        print(f"\nWARNING: {len(summa_rows)} rows still contain 'Summa' in country column!")
        print(summa_rows[["year", "country", "city"]].head(10))

    # Show unique countries for quick sanity check
    print(f"\nUnique countries ({combined['country'].nunique()}):")
    for c in sorted(combined["country"].unique()):
        print(f"  {c}")


if __name__ == "__main__":
    main()
