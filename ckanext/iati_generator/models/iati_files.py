from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, types, func
from sqlalchemy import Integer, DateTime

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin
from ckanext.iati_generator.models.enums import IATIFileTypes


DEFAULT_NAMESPACE = "iati-xml"


class IATIFile(toolkit.BaseModel, ActiveRecordMixin):
    """
    Model to represent IATI files related to CKAN packages and resources
    """
    __tablename__ = "iati_files"

    # Internal Primary key
    id = Column(Integer, primary_key=True)
    namespace = Column(types.UnicodeText, nullable=False, default=DEFAULT_NAMESPACE)
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

    is_valid = Column(types.Boolean, nullable=False, default=False)
    last_processed = Column(DateTime, nullable=True)
    last_processed_success = Column(DateTime, nullable=True)
    last_error = Column(types.UnicodeText, nullable=True)

    # TODO allow disable this file temporarily without deleting it

    def __repr__(self):
        file_type_str = IATIFileTypes(self.file_type).name
        return f"<IATIFile(id={self.id}, file_type={file_type_str}, resource_id={self.resource_id})>"

    def __str__(self):
        file_type_str = IATIFileTypes(self.file_type).name
        return f"IATIFile: {file_type_str} (Resource ID: {self.resource_id})"

    def track_processing(self, success=True, error_message=None):
        """
        Update the processing status of this IATI file.

        Parameters:
            success (bool): Whether the processing was successful. Defaults to True.
            error_message (str or None): Error message if processing failed. Defaults to None.
        """
        self.last_processed = datetime.now(timezone.utc)
        self.is_valid = success
        if success:
            self.last_processed_success = self.last_processed
        else:
            self.last_error = error_message

        # The base class ActiveRecordMixin include save and other methods
        self.save()
