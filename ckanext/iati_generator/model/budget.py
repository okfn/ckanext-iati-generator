from sqlalchemy import Column, ForeignKey, Table, func
from sqlalchemy import Integer, String, DateTime, Numeric
from sqlalchemy.orm import relationship

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin


# Association table for many-to-many relationship between organizations and documents
org_document_association = Table(
    'iati_org_document_association',
    toolkit.BaseModel.metadata,
    Column('org_id', Integer, ForeignKey('iati_organization.id')),
    Column('document_id', Integer, ForeignKey('iati_organization_document.id'))
)


class IATIOrganizationBudget(toolkit.BaseModel, ActiveRecordMixin):
    """
    IATI Organization Budget model representing budget information.

    Supports different budget types: total-budget, recipient-org-budget,
    recipient-country-budget, recipient-region-budget.
    """
    __tablename__ = "iati_organization_budget"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key to organization
    org_id = Column(Integer, ForeignKey('iati_organization.id'), nullable=False)

    # Budget core information
    budget_type = Column(String(50), nullable=False)  # total-budget, recipient-org-budget, etc.
    status = Column(String(10), default="2")  # 1=Indicative, 2=Committed

    # Period information
    period_start = Column(String(10))  # ISO date YYYY-MM-DD
    period_end = Column(String(10))    # ISO date YYYY-MM-DD

    # Value information
    value = Column(Numeric(precision=15, scale=2))
    currency = Column(String(3))
    value_date = Column(String(10))  # ISO date for exchange rate

    # Recipient organization fields (for recipient-org-budget)
    recipient_org_ref = Column(String(200))
    recipient_org_type = Column(String(10))
    recipient_org_name = Column(String(500))

    # Recipient country fields (for recipient-country-budget)
    recipient_country_code = Column(String(2))  # ISO 3166-1 alpha-2
    recipient_country_name = Column(String(200))

    # Recipient region fields (for recipient-region-budget)
    recipient_region_code = Column(String(10))
    recipient_region_vocabulary = Column(String(10), default="1")
    recipient_region_name = Column(String(200))

    # Metadata
    created_datetime = Column(DateTime, server_default=func.now())

    # Relationships
    organization = relationship("IATIOrganization", back_populates="budgets")
    budget_lines = relationship(
        "IATIOrganizationBudgetLine", back_populates="budget",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<IATIOrganizationBudget(id={self.id}, type='{self.budget_type}', value={self.value})>"
