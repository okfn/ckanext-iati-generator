from sqlalchemy import Column, ForeignKey, func
from sqlalchemy import Integer, String, Text, DateTime, Numeric
from sqlalchemy.orm import relationship

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin


class IATIOrganizationExpenseLine(toolkit.BaseModel, ActiveRecordMixin):
    """
    IATI Organization Expense Line model for detailed expenditure breakdowns.
    """
    __tablename__ = "iati_organization_expense_line"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key to expenditure
    expenditure_id = Column(Integer, ForeignKey('iati_organization_expenditure.id'), nullable=False)

    # Expense line information
    ref = Column(String(100))
    value = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3))
    value_date = Column(String(10))

    # Narrative/description
    narrative_text = Column(Text)
    narrative_lang = Column(String(5))

    # Metadata
    created_datetime = Column(DateTime, server_default=func.now())

    # Relationships
    expenditure = relationship("IATIOrganizationExpenditure", back_populates="expense_lines")

    def __repr__(self):
        return f"<IATIOrganizationExpenseLine(id={self.id}, ref='{self.ref}', value={self.value})>"
