from pathlib import Path
import pandas as pd


# =========================================================
# Ontario Rental Market Intelligence
# Statistics Canada Source Extraction
#
# Source:
# Statistics Canada Table 11-10-0017-01
# Census families by family type and family composition
#
# Purpose:
# Extract the 15 project markets for 2019-2023 using
# Median after-tax family income.
#
# Python is used only for source extraction and validation.
# Analytical transformations will be performed in PostgreSQL.
# =========================================================


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STATCAN_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "statcan"
    / "11100017-eng"
    / "11100017.csv"
)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "statcan_family_income_2019_2023.csv"
)


# ---------------------------------------------------------
# Target source selections
# ---------------------------------------------------------

TARGET_YEARS = [
    2019,
    2020,
    2021,
    2022,
    2023,
]

TARGET_CENSUS_FAMILY_TYPE = (
    "All family units"
)

TARGET_FAMILY_COMPOSITION = (
    "Family types with or without children"
)

TARGET_STATISTIC = (
    "Median after-tax family income"
)


# ---------------------------------------------------------
# Target StatsCan geographies
# ---------------------------------------------------------
#
# Exact GEO labels were verified from the source file.
# Exact matching prevents false matches such as:
#
# Windsor, Ontario
# vs.
# Grand Falls-Windsor, Newfoundland and Labrador
#
# Original StatsCan GEO values are preserved in the output.
# Market standardization will be performed later in SQL.
# ---------------------------------------------------------

TARGET_GEOGRAPHIES = {
    "Barrie, Ontario",
    "Belleville-Quinte West, Ontario",
    "Brantford, Ontario",
    "Greater Sudbury, Ontario",
    "Guelph, Ontario",
    "Hamilton, Ontario",
    "Kingston, Ontario",
    "Kitchener-Cambridge-Waterloo, Ontario",
    "London, Ontario",
    "Oshawa, Ontario",
    "Ottawa-Gatineau, Ontario part",
    "St. Catharines-Niagara, Ontario",
    "Thunder Bay, Ontario",
    "Toronto, Ontario",
    "Windsor, Ontario",
}


# ---------------------------------------------------------
# Validate source file
# ---------------------------------------------------------

if not STATCAN_FILE.exists():
    raise FileNotFoundError(
        "Statistics Canada source file not found:\n"
        f"{STATCAN_FILE}"
    )

print("Statistics Canada source file found.")
print(f"  {STATCAN_FILE}")


# ---------------------------------------------------------
# Read only fields needed for the project
# ---------------------------------------------------------

USE_COLUMNS = [
    "REF_DATE",
    "GEO",
    "DGUID",
    "Census family type",
    "Family type composition",
    "Statistics",
    "UOM",
    "SCALAR_FACTOR",
    "VALUE",
    "STATUS",
    "SYMBOL",
    "TERMINATED",
    "DECIMALS",
]

print("\nReading Statistics Canada source data...")

df = pd.read_csv(
    STATCAN_FILE,
    usecols=USE_COLUMNS,
    low_memory=False,
)

print(
    f"  Source rows read: {len(df):,}"
)


# ---------------------------------------------------------
# Apply source-selection criteria
# ---------------------------------------------------------

filtered = df[
    (df["REF_DATE"].isin(TARGET_YEARS))
    & (
        df["Census family type"]
        == TARGET_CENSUS_FAMILY_TYPE
    )
    & (
        df["Family type composition"]
        == TARGET_FAMILY_COMPOSITION
    )
    & (
        df["Statistics"]
        == TARGET_STATISTIC
    )
    & (
        df["GEO"].isin(TARGET_GEOGRAPHIES)
    )
].copy()


# ---------------------------------------------------------
# QA constants
# ---------------------------------------------------------

EXPECTED_MARKETS = 15
EXPECTED_YEARS = 5

EXPECTED_ROWS = (
    EXPECTED_MARKETS
    * EXPECTED_YEARS
)


# ---------------------------------------------------------
# QA 1: Expected record count
# ---------------------------------------------------------

print("\nRunning extraction QA checks...")

if len(filtered) != EXPECTED_ROWS:

    print("\nMatched GEO values:")

    matched_geographies = (
        filtered["GEO"]
        .drop_duplicates()
        .sort_values()
    )

    print(
        matched_geographies.to_string(
            index=False
        )
    )

    raise ValueError(
        f"Expected {EXPECTED_ROWS} target observations "
        f"({EXPECTED_MARKETS} markets x "
        f"{EXPECTED_YEARS} years), "
        f"but found {len(filtered)}."
    )

print(
    f"  PASS - Expected record count: "
    f"{EXPECTED_ROWS}"
)


# ---------------------------------------------------------
# QA 2: Exactly 15 markets
# ---------------------------------------------------------

market_count = (
    filtered["GEO"].nunique()
)

if market_count != EXPECTED_MARKETS:
    raise ValueError(
        f"Expected {EXPECTED_MARKETS} markets, "
        f"but found {market_count}."
    )

print(
    "  PASS - 15 target markets found"
)


# ---------------------------------------------------------
# QA 3: Exactly 2019-2023
# ---------------------------------------------------------

years_found = sorted(
    filtered["REF_DATE"]
    .unique()
    .tolist()
)

if years_found != TARGET_YEARS:
    raise ValueError(
        f"Expected years {TARGET_YEARS}, "
        f"but found {years_found}."
    )

print(
    "  PASS - Years 2019-2023 found"
)


# ---------------------------------------------------------
# QA 4: One observation per market-year
# ---------------------------------------------------------

duplicate_mask = filtered.duplicated(
    subset=[
        "GEO",
        "REF_DATE",
    ],
    keep=False,
)

if duplicate_mask.any():

    duplicate_rows = filtered.loc[
        duplicate_mask,
        [
            "GEO",
            "REF_DATE",
            "VALUE",
        ],
    ]

    print(
        "\nDuplicate market-year observations:"
    )

    print(
        duplicate_rows.to_string(
            index=False
        )
    )

    raise ValueError(
        "Duplicate market-year observations found."
    )

print(
    "  PASS - No duplicate market-year observations"
)


# ---------------------------------------------------------
# QA 5: Five observations per market
# ---------------------------------------------------------

rows_per_market = (
    filtered
    .groupby("GEO")
    .size()
)

if not (rows_per_market == EXPECTED_YEARS).all():

    print("\nRows per market:")

    print(
        rows_per_market.to_string()
    )

    raise ValueError(
        "At least one market does not contain "
        "exactly five annual observations."
    )

print(
    "  PASS - Every market has 5 observations"
)


# ---------------------------------------------------------
# QA 6: Fifteen observations per year
# ---------------------------------------------------------

rows_per_year = (
    filtered
    .groupby("REF_DATE")
    .size()
)

if not (rows_per_year == EXPECTED_MARKETS).all():

    print("\nRows per year:")

    print(
        rows_per_year.to_string()
    )

    raise ValueError(
        "At least one year does not contain "
        "exactly 15 market observations."
    )

print(
    "  PASS - Every year has 15 observations"
)


# ---------------------------------------------------------
# QA 7: No missing income values
# ---------------------------------------------------------

missing_values = (
    filtered["VALUE"]
    .isna()
    .sum()
)

if missing_values > 0:
    raise ValueError(
        f"Found {missing_values} missing "
        f"income values."
    )

print(
    "  PASS - No missing income values"
)


# ---------------------------------------------------------
# QA 8: Confirm exact geography coverage
# ---------------------------------------------------------

geographies_found = set(
    filtered["GEO"].unique()
)

missing_geographies = (
    TARGET_GEOGRAPHIES
    - geographies_found
)

unexpected_geographies = (
    geographies_found
    - TARGET_GEOGRAPHIES
)

if missing_geographies:
    raise ValueError(
        "Missing target geographies: "
        f"{sorted(missing_geographies)}"
    )

if unexpected_geographies:
    raise ValueError(
        "Unexpected geographies found: "
        f"{sorted(unexpected_geographies)}"
    )

print(
    "  PASS - Exact target geography coverage confirmed"
)


# ---------------------------------------------------------
# Display geography coverage
# ---------------------------------------------------------

print("\nStatsCan geographies included:")

for geography in sorted(
    geographies_found
):
    print(
        f"  - {geography}"
    )


# ---------------------------------------------------------
# Prepare source-preserving staging output
# ---------------------------------------------------------
#
# No standardized market field is created here.
#
# GEO remains exactly as published by Statistics Canada.
# Market standardization belongs in PostgreSQL.
# ---------------------------------------------------------

OUTPUT_COLUMNS = [
    "REF_DATE",
    "GEO",
    "DGUID",
    "Census family type",
    "Family type composition",
    "Statistics",
    "UOM",
    "SCALAR_FACTOR",
    "VALUE",
    "STATUS",
    "SYMBOL",
    "TERMINATED",
    "DECIMALS",
]

output_df = (
    filtered[OUTPUT_COLUMNS]
    .sort_values(
        [
            "REF_DATE",
            "GEO",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ---------------------------------------------------------
# Final output validation
# ---------------------------------------------------------

if len(output_df) != EXPECTED_ROWS:
    raise ValueError(
        "Final output record count changed "
        "unexpectedly before export."
    )


# ---------------------------------------------------------
# Export validated staging dataset
# ---------------------------------------------------------

output_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ---------------------------------------------------------
# Completion summary
# ---------------------------------------------------------

print(
    "\nAll StatsCan extraction QA checks passed."
)

print("\nExport complete:")

print(
    f"  {OUTPUT_FILE}"
)

print(
    f"  Rows: {len(output_df):,}"
)

print(
    f"  Columns: {len(output_df.columns)}"
)