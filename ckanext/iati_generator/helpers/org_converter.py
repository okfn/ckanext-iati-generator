"""
IATI Organization Data Converter

This module provides conversion between the OKFN-IATI library models
and the CKAN database models for IATI organizations.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from ..model.org import (
    IATIOrganization,
    IATIOrganizationBudget,
    IATIOrganizationBudgetLine,
    IATIOrganizationExpenditure,
    IATIOrganizationExpenseLine,
    IATIOrganizationDocument,
)

from okfn_iati.organisation_xml_generator import (
    OrganisationRecord,
    OrganisationBudget,
    OrganisationExpenditure,
    OrganisationDocument
)


logger = logging.getLogger(__name__)


class IATIOrganizationConverter:
    """
    Converter between OKFN-IATI library models and CKAN database models.
    """

    @staticmethod
    def library_to_db(org_record: 'OrganisationRecord',
                      package_id: Optional[str] = None) -> IATIOrganization:
        """
        Convert an OrganisationRecord from the library to a database model.

        Args:
            org_record: OrganisationRecord from okfn_iati library
            package_id: CKAN package ID to associate with

        Returns:
            IATIOrganization: Database model instance
        """

        # Create main organization record
        db_org = IATIOrganization(
            package_id=package_id,
            org_identifier=org_record.org_identifier,
            name=org_record.name,
            reporting_org_ref=org_record.reporting_org_ref,
            reporting_org_type=org_record.reporting_org_type,
            reporting_org_name=org_record.reporting_org_name,
            title=org_record.name,  # Default title to name
            last_updated_datetime=datetime.utcnow()
        )

        # Convert budgets
        for budget in org_record.budgets:
            db_budget = IATIOrganizationConverter._convert_budget_to_db(budget)
            db_org.budgets.append(db_budget)

        # Convert expenditures
        for expenditure in org_record.expenditures:
            db_expenditure = IATIOrganizationConverter._convert_expenditure_to_db(expenditure)
            db_org.expenditures.append(db_expenditure)

        # Convert documents
        for document in org_record.documents:
            db_document = IATIOrganizationConverter._convert_document_to_db(document)
            db_org.documents.append(db_document)

        return db_org

    @staticmethod
    def _convert_budget_to_db(budget: 'OrganisationBudget') -> IATIOrganizationBudget:
        """Convert OrganisationBudget to IATIOrganizationBudget."""
        db_budget = IATIOrganizationBudget(
            budget_type=budget.kind,
            status=budget.status,
            period_start=budget.period_start,
            period_end=budget.period_end,
            value=float(budget.value) if budget.value else None,
            currency=budget.currency,
            value_date=budget.value_date,
            recipient_org_ref=budget.recipient_org_ref,
            recipient_org_type=budget.recipient_org_type,
            recipient_org_name=budget.recipient_org_name,
            recipient_country_code=budget.recipient_country_code,
            recipient_region_code=budget.recipient_region_code,
            recipient_region_vocabulary=budget.recipient_region_vocabulary
        )

        # Convert budget lines
        for line_data in budget.budget_lines:
            if 'value' in line_data:
                budget_line = IATIOrganizationBudgetLine(
                    ref=line_data.get('ref', ''),
                    value=float(line_data['value']),
                    currency=line_data.get('currency', budget.currency),
                    value_date=line_data.get('value_date', budget.value_date),
                    narrative_text=line_data.get('narrative', ''),
                    narrative_lang=line_data.get('lang', 'en')
                )
                db_budget.budget_lines.append(budget_line)

        return db_budget

    @staticmethod
    def _convert_expenditure_to_db(expenditure: 'OrganisationExpenditure') -> IATIOrganizationExpenditure:
        """Convert OrganisationExpenditure to IATIOrganizationExpenditure."""
        db_expenditure = IATIOrganizationExpenditure(
            period_start=expenditure.period_start,
            period_end=expenditure.period_end,
            value=float(expenditure.value),
            currency=expenditure.currency,
            value_date=expenditure.value_date
        )

        # Convert expense lines
        for line_data in expenditure.expense_lines:
            if 'value' in line_data:
                expense_line = IATIOrganizationExpenseLine(
                    ref=line_data.get('ref', ''),
                    value=float(line_data['value']),
                    currency=line_data.get('currency', expenditure.currency),
                    value_date=line_data.get('value_date', expenditure.value_date),
                    narrative_text=line_data.get('narrative', ''),
                    narrative_lang=line_data.get('lang', 'en')
                )
                db_expenditure.expense_lines.append(expense_line)

        return db_expenditure

    @staticmethod
    def _convert_document_to_db(document: 'OrganisationDocument') -> IATIOrganizationDocument:
        """Convert OrganisationDocument to IATIOrganizationDocument."""
        return IATIOrganizationDocument(
            url=document.url,
            format=document.format,
            title=document.title,
            category_code=document.category_code,
            language_code=document.language,
            document_date=document.document_date
        )

    @staticmethod
    def db_to_library(db_org: IATIOrganization) -> 'OrganisationRecord':
        """
        Convert a database IATIOrganization to library OrganisationRecord.

        Args:
            db_org: Database model instance

        Returns:
            OrganisationRecord: Library model instance
        """

        # Convert budgets
        budgets = []
        for db_budget in db_org.budgets:
            budget = OrganisationBudget(
                kind=db_budget.budget_type,
                status=db_budget.status,
                period_start=db_budget.period_start,
                period_end=db_budget.period_end,
                value=str(db_budget.value) if db_budget.value else None,
                currency=db_budget.currency,
                value_date=db_budget.value_date,
                recipient_org_ref=db_budget.recipient_org_ref,
                recipient_org_type=db_budget.recipient_org_type,
                recipient_org_name=db_budget.recipient_org_name,
                recipient_country_code=db_budget.recipient_country_code,
                recipient_region_code=db_budget.recipient_region_code,
                recipient_region_vocabulary=db_budget.recipient_region_vocabulary,
                budget_lines=[
                    {
                        'ref': line.ref or '',
                        'value': str(line.value),
                        'currency': line.currency,
                        'value_date': line.value_date,
                        'narrative': line.narrative_text or '',
                        'lang': line.narrative_lang or 'en'
                    }
                    for line in db_budget.budget_lines
                ]
            )
            budgets.append(budget)

        # Convert expenditures
        expenditures = []
        for db_exp in db_org.expenditures:
            expenditure = OrganisationExpenditure(
                period_start=db_exp.period_start,
                period_end=db_exp.period_end,
                value=str(db_exp.value),
                currency=db_exp.currency,
                value_date=db_exp.value_date,
                expense_lines=[
                    {
                        'ref': line.ref or '',
                        'value': str(line.value),
                        'currency': line.currency,
                        'value_date': line.value_date,
                        'narrative': line.narrative_text or '',
                        'lang': line.narrative_lang or 'en'
                    }
                    for line in db_exp.expense_lines
                ]
            )
            expenditures.append(expenditure)

        # Convert documents
        documents = []
        for db_doc in db_org.documents:
            document = OrganisationDocument(
                url=db_doc.url,
                format=db_doc.format,
                title=db_doc.title,
                category_code=db_doc.category_code,
                language=db_doc.language_code,
                document_date=db_doc.document_date
            )
            documents.append(document)

        # Create and return OrganisationRecord
        return OrganisationRecord(
            org_identifier=db_org.org_identifier,
            name=db_org.name,
            reporting_org_ref=db_org.reporting_org_ref,
            reporting_org_type=db_org.reporting_org_type,
            reporting_org_name=db_org.reporting_org_name,
            budgets=budgets,
            expenditures=expenditures,
            documents=documents
        )

    @staticmethod
    def create_from_csv_data(
        csv_data: Dict[str, Any],
        package_id: Optional[str] = None
    ) -> IATIOrganization:
        """
        Create database model directly from CSV data without using library models.

        Args:
            csv_data: Dictionary containing CSV row data
            package_id: CKAN package ID to associate with

        Returns:
            IATIOrganization: Database model instance
        """
        def get_value(key: str, default: str = "") -> str:
            """Get value from CSV data, handling various key formats."""
            # Try exact match first
            if key in csv_data:
                value = csv_data[key]
                return str(value).strip() if value is not None else default

            # Try case-insensitive match
            key_lower = key.lower()
            for csv_key, csv_value in csv_data.items():
                if csv_key.lower() == key_lower:
                    return str(csv_value).strip() if csv_value is not None else default

            return default

        # Create main organization
        db_org = IATIOrganization(
            package_id=package_id,
            org_identifier=get_value("Organisation Identifier") or get_value("org_identifier"),
            name=get_value("Name") or get_value("name"),
            reporting_org_ref=get_value("Reporting Org Ref") or get_value("reporting_org_ref"),
            reporting_org_type=get_value("Reporting Org Type") or get_value("reporting_org_type"),
            reporting_org_name=get_value("Reporting Org Name") or get_value("reporting_org_name"),
            last_updated_datetime=datetime.utcnow()
        )

        # Set title to name if not provided
        db_org.title = db_org.name

        # Create budget if data is present
        budget_kind = get_value("Budget Kind") or get_value("budget_kind")
        budget_value = get_value("Budget Value") or get_value("budget_value")

        if budget_kind and budget_value:
            try:
                db_budget = IATIOrganizationBudget(
                    budget_type=budget_kind,
                    status=get_value("Budget Status") or get_value("budget_status") or "2",
                    period_start=get_value("Budget Period Start") or get_value("budget_start"),
                    period_end=get_value("Budget Period End") or get_value("budget_end"),
                    value=float(budget_value),
                    currency=get_value("Currency") or get_value("budget_currency") or "USD",
                    value_date=get_value("Value Date") or get_value("budget_value_date"),
                    recipient_org_ref=get_value("Recipient Org Ref") or get_value("recipient_org_ref"),
                    recipient_org_type=get_value("Recipient Org Type") or get_value("recipient_org_type"),
                    recipient_org_name=get_value("Recipient Org Name") or get_value("recipient_org_name"),
                    recipient_country_code=get_value("Recipient Country Code") or get_value("recipient_country_code"),
                    recipient_region_code=get_value("Recipient Region Code") or get_value("recipient_region_code"),
                    recipient_region_vocabulary=get_value(
                        "Recipient Region Vocabulary"
                    ) or get_value("recipient_region_vocabulary")
                )
                db_org.budgets.append(db_budget)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse budget value '{budget_value}': {e}")

        # Create expenditure if data is present
        exp_value = get_value("Expenditure Value") or get_value("expenditure_value")
        exp_start = get_value("Expenditure Period Start") or get_value("expenditure_start")
        exp_end = get_value("Expenditure Period End") or get_value("expenditure_end")

        if exp_value and exp_start and exp_end:
            try:
                db_expenditure = IATIOrganizationExpenditure(
                    period_start=exp_start,
                    period_end=exp_end,
                    value=float(exp_value),
                    currency=get_value("Expenditure Currency") or get_value("expenditure_currency") or "USD",
                    value_date=get_value("Expenditure Date") or get_value("expenditure_value_date")
                )
                db_org.expenditures.append(db_expenditure)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse expenditure value '{exp_value}': {e}")

        # Create document if URL is present
        doc_url = get_value("Document URL") or get_value("document_url")
        if doc_url:
            db_document = IATIOrganizationDocument(
                url=doc_url,
                format=get_value("Document Format") or get_value("document_format") or "text/html",
                title=get_value("Document Title") or get_value("document_title") or "Supporting Document",
                category_code=get_value("Document Category") or get_value("document_category") or "A01",
                language_code=get_value("Document Language") or get_value("document_language") or "en",
                document_date=get_value("Document Date") or get_value("document_date")
            )
            db_org.documents.append(db_document)

        return db_org
