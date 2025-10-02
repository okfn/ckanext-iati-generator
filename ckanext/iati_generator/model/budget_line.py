from sqlalchemy import Column, ForeignKey, Table, func
from sqlalchemy import Integer, String, Text, DateTime, Numeric
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


class IATIOrganizationBudgetLine(toolkit.BaseModel, ActiveRecordMixin):
    """
    IATI Organization Budget Line model for detailed budget breakdowns.
    """
    __tablename__ = "iati_organization_budget_line"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key to budget
    budget_id = Column(Integer, ForeignKey('iati_organization_budget.id'), nullable=False)

    # Budget line information
    ref = Column(String(100))  # Reference/identifier for the budget line
    value = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3))
    value_date = Column(String(10))

    # Narrative/description
    narrative_text = Column(Text)
    narrative_lang = Column(String(5))

    # Metadata
    created_datetime = Column(DateTime, server_default=func.now())

    # Relationships
    budget = relationship("IATIOrganizationBudget", back_populates="budget_lines")

    def __repr__(self):
        return f"<IATIOrganizationBudgetLine(id={self.id}, ref='{self.ref}', value={self.value})>"
