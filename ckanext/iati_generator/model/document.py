from sqlalchemy import Column, func
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin

from ckanext.iati_generator.model.org import org_document_association


class IATIOrganizationDocument(toolkit.BaseModel, ActiveRecordMixin):
    """
    IATI Organization Document Link model.

    Documents can be associated with multiple organizations via many-to-many relationship.
    """
    __tablename__ = "iati_organization_document"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Document information
    url = Column(String(1000), nullable=False)
    format = Column(String(100), default="text/html")  # MIME type

    # Document metadata
    title = Column(String(500))
    category_code = Column(String(10))  # IATI document category code
    language_code = Column(String(5))
    document_date = Column(String(10))  # ISO date when document was published

    # Additional metadata
    file_size = Column(Integer)  # File size in bytes
    description = Column(Text)

    # Metadata
    created_datetime = Column(DateTime, server_default=func.now())
    updated_datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    organizations = relationship(
        "IATIOrganization",
        secondary=org_document_association,
        back_populates="documents"
    )

    def __repr__(self):
        return f"<IATIOrganizationDocument(id={self.id}, url='{self.url}', title='{self.title}')>"
