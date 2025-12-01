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

    # ------------------------------------------------------------------
    # ACTIVITY FILE TYPES
    # Always sync IatiMultiCsvConverter.csv_files
    # https://github.com/okfn/okfn_iati/blob/main/src/okfn_iati/multi_csv_converter.py#L56
    # ------------------------------------------------------------------
    ACTIVITY_MAIN_FILE = 200
    ACTIVITY_BUDGET_FILE = 210
    ACTIVITY_EXPENDITURE_FILE = 220
    ACTIVITY_DOCUMENT_FILE = 230
    ACTIVITY_LOCATION_FILE = 240
    ACTIVITY_SECTOR_FILE = 250
    ACTIVITY_PARTNER_FILE = 260
    ACTIVITY_RESULT_FILE = 270
    ACTIVITY_TRANSACTION_FILE = 280
    ACTIVITY_POLICY_FILE = 290
