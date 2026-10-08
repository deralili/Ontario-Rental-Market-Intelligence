from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CMHC_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "cmhc"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Discover CMHC source workbooks
# ---------------------------------------------------------

cmhc_files = sorted(CMHC_RAW_DIR.glob("rmr-ontario-*-en.xlsx"))

print(f"CMHC folder: {CMHC_RAW_DIR}")
print(f"Workbooks found: {len(cmhc_files)}")

for file in cmhc_files:
    print(f"  - {file.name}")


# ---------------------------------------------------------
# Validate source files
# ---------------------------------------------------------

if len(cmhc_files) != 7:
    raise ValueError(
        f"Expected 7 CMHC workbooks for 2019-2025, "
        f"but found {len(cmhc_files)}."
    )

print("\nSource file validation passed.")


# ---------------------------------------------------------
# Validate required CMHC worksheets
# ---------------------------------------------------------

REQUIRED_SHEETS = {
    "Table 1.1.1": "Vacancy Rate",
    "Table 1.1.2": "Average Rent",
    "Table 1.1.3": "Rental Universe",
    "Table 1.1.5": "Percentage Change in Average Rent",
    "Table 1.1.6": "Turnover Rate",
}

print("\nValidating required worksheets...")

for file in cmhc_files:
    workbook = pd.ExcelFile(file)

    missing_sheets = [
        sheet
        for sheet in REQUIRED_SHEETS
        if sheet not in workbook.sheet_names
    ]

    if missing_sheets:
        raise ValueError(
            f"{file.name} is missing required sheets: "
            f"{', '.join(missing_sheets)}"
        )

    print(f"  PASS - {file.name}")

print("\nWorksheet validation passed.")


# ---------------------------------------------------------
# Inspect endpoint workbook layouts
# ---------------------------------------------------------

print("\nInspecting Average Rent sheet structure...")

for year in [2019, 2025]:
    file = next(
        file for file in cmhc_files
        if f"-{year}-" in file.name
    )

    preview = pd.read_excel(
        file,
        sheet_name="Table 1.1.2",
        header=None,
        nrows=15
    )

    print(f"\n--- {year} | Table 1.1.2 | Average Rent ---")
    print(preview.to_string(index=False, header=False))


# ---------------------------------------------------------
# Extraction configuration
# ---------------------------------------------------------

UNIT_TYPES = [
    "Bachelor",
    "Studio",
    "1 Bedroom",
    "2 Bedroom",
    "3 Bedroom +",
    "Total",
]

TARGET_CMHC_MARKETS = {
    "Barrie CMA",
    "Belleville CMA",
    "Belleville - Quinte West CMA",
    "Brantford CMA",
    "Greater Sudbury/Grand Sudbury CMA",
    "Guelph CMA",
    "Hamilton CMA",
    "Kingston CMA",
    "Kitchener-Cambridge-Waterloo CMA",
    "London CMA",
    "Oshawa CMA",
    "Ottawa-Gatineau CMA (Ont. part)",
    "St. Catharines-Niagara CMA",
    "Thunder Bay CMA",
    "Toronto CMA",
    "Windsor CMA",
}

MEASURE_CONFIG = {
    "Table 1.1.1": {
        "measure": "Vacancy Rate",
        "has_reliability": True,
        "has_change_indicator": True,
    },
    "Table 1.1.2": {
        "measure": "Average Rent",
        "has_reliability": True,
        "has_change_indicator": False,
    },
    "Table 1.1.3": {
        "measure": "Rental Universe",
        "has_reliability": False,
        "has_change_indicator": False,
    },
    "Table 1.1.5": {
        "measure": "Percentage Change in Average Rent",
        "has_reliability": True,
        "has_change_indicator": False,
    },
    "Table 1.1.6": {
        "measure": "Turnover Rate",
        "has_reliability": True,
        "has_change_indicator": True,
    },
}


def find_table_structure(df):
    """
    Locate the CMHC table header dynamically.

    Returns:
        centre_row: row containing the 'Centre' heading
        unit_row: row containing the bedroom/unit-type headings
    """

    centre_row = None

    # Find the row where the first column contains "Centre"
    for row_idx in range(len(df)):
        first_cell = df.iloc[row_idx, 0]

        if pd.notna(first_cell) and str(first_cell).strip() == "Centre":
            centre_row = row_idx
            break

    if centre_row is None:
        raise ValueError("Could not locate the 'Centre' header row.")

    # Unit-type headings are directly above the Centre/year row
    unit_row = centre_row - 1

    if unit_row < 0:
        raise ValueError(
            "Could not locate the unit-type header row."
        )

    return centre_row, unit_row


def find_current_year_columns(df, centre_row, unit_row, edition_year):
    """
    Identify the current-edition value column for each unit type.

    Returns a dictionary such as:
        {
            "Studio": 3,
            "1 Bedroom": 8,
            ...
        }

    Dictionary values are pandas column indexes.
    """

    current_year_suffix = str(edition_year)[-2:]

    unit_columns = {}
    current_unit = None

    for col_idx in range(df.shape[1]):

        # Check whether this column starts a new unit-type group
        unit_cell = df.iloc[unit_row, col_idx]

        if pd.notna(unit_cell):
            unit_text = str(unit_cell).strip()

            if unit_text in UNIT_TYPES:
                current_unit = unit_text

        if current_unit is None:
            continue

        # Examine the period/year heading
        year_cell = df.iloc[centre_row, col_idx]

        if pd.isna(year_cell):
            continue

        year_text = str(year_cell).strip()

        # Handles headings such as:
        # Oct-25
        # Oct-24 to Oct-25
        # Oct-24\nto\nOct-25
        if year_text.endswith(current_year_suffix):
            unit_columns[current_unit] = col_idx

    return unit_columns


def extract_sheet_observations(
    df,
    edition_year,
    sheet_name,
    config
):
    """
    Extract current-edition observations from one CMHC worksheet.

    Returns a list of dictionaries in long format.
    """

    centre_row, unit_row = find_table_structure(df)

    current_year_columns = find_current_year_columns(
        df,
        centre_row,
        unit_row,
        edition_year
    )

    records = []

    # Data begins immediately below the Centre/year header
    for row_idx in range(centre_row + 1, len(df)):

        market_cell = df.iloc[row_idx, 0]

        # Skip rows without a market/geography name
        if pd.isna(market_cell):
            continue

        market_raw = str(market_cell).strip()

        # Keep only the 15 target Ontario rental markets.
        # Historical CMHC source names are preserved as published.
        if market_raw not in TARGET_CMHC_MARKETS:
            continue

        for unit_type, value_col in current_year_columns.items():

            value = df.iloc[row_idx, value_col]

            # Preserve the raw published value.
            value_raw = "" if pd.isna(value) else str(value).strip()

            reliability_code = ""
            change_indicator = ""

            # Reliability code appears immediately after the value.
            if config["has_reliability"]:
                reliability_col = value_col + 1

                if reliability_col < df.shape[1]:
                    reliability_value = df.iloc[
                        row_idx,
                        reliability_col
                    ]

                    if pd.notna(reliability_value):
                        reliability_code = str(
                            reliability_value
                        ).strip()

            # Vacancy and turnover tables include a change
            # indicator after the current-year reliability code.
            if config["has_change_indicator"]:
                change_col = value_col + 2

                if change_col < df.shape[1]:
                    change_value = df.iloc[
                        row_idx,
                        change_col
                    ]

                    if pd.notna(change_value):
                        change_indicator = str(
                            change_value
                        ).strip()

            records.append(
                {
                    "edition_year": edition_year,
                    "observation_year": edition_year,
                    "market_raw": market_raw,
                    "unit_type_raw": unit_type,
                    "measure": config["measure"],
                    "value_raw": value_raw,
                    "reliability_code": reliability_code,
                    "change_indicator": change_indicator,
                    "source_sheet": sheet_name,
                }
            )

    return records


# ---------------------------------------------------------
# Extract and validate all CMHC observations
# ---------------------------------------------------------

print("\nExtracting target-market observations...")

all_records = []

for file in cmhc_files:

    edition_year = int(file.stem.split("-")[2])

    year_records = []

    for sheet_name, config in MEASURE_CONFIG.items():

        df = pd.read_excel(
            file,
            sheet_name=sheet_name,
            header=None
        )

        sheet_records = extract_sheet_observations(
            df=df,
            edition_year=edition_year,
            sheet_name=sheet_name,
            config=config
        )

        year_records.extend(sheet_records)

    all_records.extend(year_records)

    print(
        f"  {edition_year}: "
        f"{len(year_records):,} records"
    )

cmhc_df = pd.DataFrame(all_records)

print(
    f"\nTotal records extracted: "
    f"{len(cmhc_df):,}"
)

print("\nRecords by edition year:")
print(
    cmhc_df.groupby("edition_year")
    .size()
    .to_string()
)

print("\nUnique raw markets by edition year:")
print(
    cmhc_df.groupby("edition_year")["market_raw"]
    .nunique()
    .to_string()
)

cmhc_df = pd.DataFrame(all_records)


# ---------------------------------------------------------
# Final extraction QA checks
# ---------------------------------------------------------

print("\nRunning final extraction QA checks...")

# 1. Expected total number of records
expected_records = 15 * 7 * 5 * 5

if len(cmhc_df) != expected_records:
    raise ValueError(
        f"Expected {expected_records:,} records, "
        f"but found {len(cmhc_df):,}."
    )

print(f"  PASS - Expected record count: {expected_records:,}")


# 2. Check for duplicate observation keys
duplicate_mask = cmhc_df.duplicated(
    subset=[
        "edition_year",
        "market_raw",
        "unit_type_raw",
        "measure",
    ],
    keep=False
)

duplicate_count = duplicate_mask.sum()

if duplicate_count > 0:
    raise ValueError(
        f"Found {duplicate_count} records with duplicate "
        f"observation keys."
    )

print("  PASS - No duplicate observation keys")


# 3. Confirm every edition contains all five measures
measure_counts = (
    cmhc_df.groupby("edition_year")["measure"]
    .nunique()
)

if not (measure_counts == 5).all():
    raise ValueError(
        "At least one edition does not contain all five measures."
    )

print("  PASS - All editions contain 5 measures")


# 4. Confirm suppressed/source-coded values were preserved
special_values = cmhc_df[
    cmhc_df["value_raw"].isin(["**", "++"])
]

if special_values.empty:
    raise ValueError(
        "No suppressed/source-coded values were found. "
        "Check raw-value preservation."
    )

print(
    f"  PASS - Preserved {len(special_values):,} "
    f"special source values (** / ++)"
)


# 5. Known 2024 Toronto 2-bedroom QA observations
qa_expected = {
    "Average Rent": "1974",
    "Vacancy Rate": "1.9",
    "Rental Universe": "143941",
}

for measure, expected_value in qa_expected.items():

    match = cmhc_df[
        (cmhc_df["edition_year"] == 2024)
        & (cmhc_df["market_raw"] == "Toronto CMA")
        & (cmhc_df["unit_type_raw"] == "2 Bedroom")
        & (cmhc_df["measure"] == measure)
    ]

    if len(match) != 1:
        raise ValueError(
            f"Expected exactly one Toronto 2024 "
            f"2 Bedroom {measure} observation."
        )

    actual_value = (
        str(match.iloc[0]["value_raw"])
        .replace(",", "")
        .strip()
    )

    if actual_value != expected_value:
        raise ValueError(
            f"Toronto 2024 2 Bedroom {measure}: "
            f"expected {expected_value}, "
            f"found {actual_value}."
        )

    print(
        f"  PASS - Toronto 2024 2 Bedroom "
        f"{measure}: {actual_value}"
    )


print("\nAll extraction QA checks passed.")


# ---------------------------------------------------------
# Export validated CMHC staging dataset
# ---------------------------------------------------------

output_file = PROCESSED_DIR / "cmhc_rental_market_2019_2025.csv"

cmhc_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8"
)

print(f"\nExport complete:")
print(f"  {output_file}")
print(f"  Rows: {len(cmhc_df):,}")
print(f"  Columns: {len(cmhc_df.columns)}")