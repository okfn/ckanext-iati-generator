from enum import Enum


class IATIFileTypes(Enum):
    """ IATI elements are contained in files for each type of data """
    # ------------------------------------------------------------------
    # ORGANIZATION FILE TYPES
    # ------------------------------------------------------------------
    ORGANIZATION_MAIN_FILE = 100
    ORGANIZATION_NAMES_FILE = 110
    ORGANIZATION_BUDGET_FILE = 120
    ORGANIZATION_EXPENDITURE_FILE = 130
    ORGANIZATION_DOCUMENT_FILE = 140
    FINAL_ORGANIZATION_FILE = 199

    # ------------------------------------------------------------------
    # ACTIVITY FILE TYPES
    # Always sync IatiMultiCsvConverter.csv_files
    # https://github.com/okfn/okfn_iati/blob/main/src/okfn_iati/multi_csv_converter.py#L56
    # ------------------------------------------------------------------
    ACTIVITY_MAIN_FILE = 200                     # activities.csv
    ACTIVITY_PARTICIPATING_ORGS_FILE = 210       # participating_orgs.csv
    ACTIVITY_SECTORS_FILE = 220                  # sectors.csv
    ACTIVITY_BUDGET_FILE = 230                   # budgets.csv
    ACTIVITY_TRANSACTIONS_FILE = 240             # transactions.csv
    ACTIVITY_TRANSACTION_SECTORS_FILE = 250      # transaction_sectors.csv
    ACTIVITY_LOCATIONS_FILE = 260                # locations.csv
    ACTIVITY_DOCUMENTS_FILE = 270                # documents.csv
    ACTIVITY_RESULTS_FILE = 280                  # results.csv
    ACTIVITY_INDICATORS_FILE = 290               # indicators.csv
    ACTIVITY_INDICATOR_PERIODS_FILE = 300        # indicator_periods.csv
    ACTIVITY_DATES_FILE = 310                    # activity_date.csv
    ACTIVITY_CONTACT_INFO_FILE = 320             # contact_info.csv
    ACTIVITY_CONDITIONS_FILE = 330               # conditions.csv
    ACTIVITY_DESCRIPTIONS_FILE = 340             # descriptions.csv
    ACTIVITY_COUNTRY_BUDGET_ITEMS_FILE = 350     # country_budget_items.csv
    FINAL_ACTIVITY_FILE = 299


# Mapping from activity file type enum values to their CSV filenames.
# Keep in sync with IatiMultiCsvConverter.csv_files in okfn_iati.
ACTIVITY_CSV_FILENAMES = {
    IATIFileTypes.ACTIVITY_MAIN_FILE: "activities.csv",
    IATIFileTypes.ACTIVITY_PARTICIPATING_ORGS_FILE: "participating_orgs.csv",
    IATIFileTypes.ACTIVITY_SECTORS_FILE: "sectors.csv",
    IATIFileTypes.ACTIVITY_BUDGET_FILE: "budgets.csv",
    IATIFileTypes.ACTIVITY_TRANSACTIONS_FILE: "transactions.csv",
    IATIFileTypes.ACTIVITY_TRANSACTION_SECTORS_FILE: "transaction_sectors.csv",
    IATIFileTypes.ACTIVITY_LOCATIONS_FILE: "locations.csv",
    IATIFileTypes.ACTIVITY_DOCUMENTS_FILE: "documents.csv",
    IATIFileTypes.ACTIVITY_RESULTS_FILE: "results.csv",
    IATIFileTypes.ACTIVITY_INDICATORS_FILE: "indicators.csv",
    IATIFileTypes.ACTIVITY_INDICATOR_PERIODS_FILE: "indicator_periods.csv",
    IATIFileTypes.ACTIVITY_DATES_FILE: "activity_date.csv",
    IATIFileTypes.ACTIVITY_CONTACT_INFO_FILE: "contact_info.csv",
    IATIFileTypes.ACTIVITY_CONDITIONS_FILE: "conditions.csv",
    IATIFileTypes.ACTIVITY_DESCRIPTIONS_FILE: "descriptions.csv",
    IATIFileTypes.ACTIVITY_COUNTRY_BUDGET_ITEMS_FILE: "country_budget_items.csv",
}

# Reverse mapping: CSV filename -> enum value (as string), for matching validation issues
CSV_FILENAME_TO_FILE_TYPE = {fname: str(ft.value) for ft, fname in ACTIVITY_CSV_FILENAMES.items()}
