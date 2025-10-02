from sqlalchemy import Column, ForeignKey, types, func
from sqlalchemy import Integer, DateTime

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin
from ckanext.iati_generator.models.enums import IATIFileTypes


class IATIFile(toolkit.BaseModel, ActiveRecordMixin):
    """
    Model to represent IATI files related to CKAN packages and resources
    """
    __tablename__ = "iati_files"

    # Internal Primary key
    id = Column(Integer, primary_key=True)
    file_type = Column(Integer, nullable=False)
    # CKAN resource (CSV or tabular data file)
    resource_id = Column(
        types.UnicodeText,
        ForeignKey('resource.id'),
        ondelete='CASCADE',
        nullable=False,
        unique=True,
        index=True,
    )

    metadata_created = Column(DateTime, server_default=func.now())
    metadata_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # TODO allow disable this file temporarily without deleting it
    # TODO if we want multiple IATI files, we probable will want a namespace to contains this file
    # this could be related to the final URL of the XML files

    def __repr__(self):
        file_type_str = IATIFileTypes(self.file_type).name
        return f"<IATIFile(id={self.id}, file_type={file_type_str}, resource_id={self.resource_id})>"

    def __str__(self):
        file_type_str = IATIFileTypes(self.file_type).name
        return f"IATIFile: {file_type_str} (Resource ID: {self.resource_id})"
