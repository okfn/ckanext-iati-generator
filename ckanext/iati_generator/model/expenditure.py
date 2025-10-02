from sqlalchemy import Column, ForeignKey, func
from sqlalchemy import Integer, String, DateTime, Numeric
from sqlalchemy.orm import relationship

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin


class IATIOrganizationExpenditure(toolkit.BaseModel, ActiveRecordMixin):
    """
    IATI Organization Total Expenditure model.
    """
    __tablename__ = "iati_organization_expenditure"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key to organization
    org_id = Column(Integer, ForeignKey('iati_organization.id'), nullable=False)

    # Period information
    period_start = Column(String(10), nullable=False)  # ISO date YYYY-MM-DD
    period_end = Column(String(10), nullable=False)    # ISO date YYYY-MM-DD

    # Value information
    value = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3))
    value_date = Column(String(10))

    # Metadata
    created_datetime = Column(DateTime, server_default=func.now())

    # Relationships
    organization = relationship("IATIOrganization", back_populates="expenditures")
    expense_lines = relationship(
        "IATIOrganizationExpenseLine", back_populates="expenditure",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<IATIOrganizationExpenditure(id={self.id}, period={self.period_start}-{self.period_end}, value={self.value})>"
