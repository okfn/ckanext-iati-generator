from sqlalchemy import Column, ForeignKey, Table, func
from sqlalchemy import Integer, String, DateTime

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin
from ckanext.iati_generator.model.narrative import IATINarrative
from ckanext.iati_generator.model.enums import IATINarrativeTypes


# Association table for many-to-many relationship between organizations and documents
org_document_association = Table(
    'iati_org_document_association',
    toolkit.BaseModel.metadata,
    Column('org_id', Integer, ForeignKey('iati_organization.id')),
    Column('document_id', Integer, ForeignKey('iati_organization_document.id'))
)


class IATIOrganization(toolkit.BaseModel, ActiveRecordMixin):
    """
    Main IATI Organization model representing an organization in the IATI standard.

    This model stores core organization information and serves as the parent
    for related budget, expenditure, and document data.
    Docs
    https://iatistandard.org/en/iati-standard/203/organisation-standard/iati-organisations/iati-organisation/
    Schema
    https://github.com/IATI/IATI-Schemas/blob/version-2.03/iati-organisations-schema.xsd#L28

    """
    __tablename__ = "iati_organization"
    # __upload_folder__ = "iati_organization_thumb"

    # Internal Primary key
    id = Column(Integer, primary_key=True)

    # IATI Core Fields
    org_identifier = Column(String(200), nullable=False, unique=True, index=True)

    # Organization name(s) are defined by the narrative.IATINarrative with narrative_type = IATINarrativeTypes.ORGANIZATION_NAME

    last_updated_datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())
    # ISO 639-1 language code https://iatistandard.org/en/iati-standard/203/codelists/Language/
    default_language = Column(String(5), default="en")
    # ISO 4217 currency code https://iatistandard.org/en/iati-standard/203/codelists/currency/
    default_currency = Column(String(3), default="USD")

    # Additional Organization Information
    # The version is for the top level XML object "iati-organizations" (with an "s" at the end)
    # iati_version = Column(String(10), default="2.03")

    # # Reporting Organization
    # reporting_org_ref = Column(String(200))
    # reporting_org_type = Column(String(10))  # IATI organization type code
    # reporting_org_name = Column(String(500))

    # # Metadata
    # last_updated_datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())
    # created_datetime = Column(DateTime, server_default=func.now())

    # # Legacy fields for CKAN display
    # embeded_url = Column(String(200))
    # report_url = Column(String(200))
    # report_title = Column(String(200), nullable=True)
    # thumbnail_url = Column(String(600))
    # title = Column(String(300))  # Display title override

    # # Relationships
    # budgets = relationship(
    #     "IATIOrganizationBudget", back_populates="organization",
    #     cascade="all, delete-orphan"
    # )
    # expenditures = relationship(
    #     "IATIOrganizationExpenditure", back_populates="organization",
    #     cascade="all, delete-orphan"
    # )
    # documents = relationship(
    #     "IATIOrganizationDocument",
    #     secondary=org_document_association,
    #     back_populates="organizations"
    # )

    def get_names(self):
        """ We expect a dict like
            {'en': 'Name in English', 'fr': 'Nom en français', ....}
        """
        # Query narratives for this organization's names
        name_narratives = IATINarrative.query.filter(
            IATINarrative.narrative_type == IATINarrativeTypes.ORGANIZATION_NAME,
            IATINarrative.related_object_id == self.id
        ).all()

        return {n.language if n.language else self.default_language: n.text for n in name_narratives}

    @property
    def name(self):
        """ Return the default name (in default language) or any name if no default """
        names = self.get_names()
        return names.get(self.default_language) or next(iter(names.values()), "Unnamed Organization")

    def __repr__(self):
        return f"<IATIOrganization(identifier='{self.org_identifier}')>"

    def __str__(self):
        return f"IATI Organization(identifier='{self.org_identifier}')"
