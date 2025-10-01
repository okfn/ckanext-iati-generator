from sqlalchemy import Column, Enum
from sqlalchemy import Integer, String, Text

from ckan.plugins import toolkit
from ckan.model.base import ActiveRecordMixin

from ckanext.iati_generator.model import IATINarrativeTypes


class IATINarrative(toolkit.BaseModel, ActiveRecordMixin):
    """
    IATI Narrative model for multilingual text content.

    Used for organization names, descriptions, activity titles, and other text fields
    that can have multiple language variants across all IATI elements.

    Docs: https://iatistandard.org/en/iati-standard/203/organisation-standard/overview/narrative/
    """
    __tablename__ = "iati_narrative"

    id = Column(Integer, primary_key=True)

    # Several IATI objects uses narratives
    # Each object also includes a narrative name (like "name", "description", "title", etc)
    # E.g. Organization have the "name" narrative:
    # <name>
    #     <narrative>Organisation name</narrative>
    #     <narrative xml:lang="fr">Nom de l'organisme</narrative>
    # </name>
    narrative_type = Column(Enum(IATINarrativeTypes), nullable=False)
    # Allow linking to any IATI object by its internal ID
    related_object_id = Column(Integer, nullable=False)

    # The text content in the specified language
    text = Column(Text, nullable=False)
    # ISO 639-1 language code
    language = Column(String(5), nullable=True)  # Can be null to inherit from parent

    def __repr__(self):
        return f"<IATINarrative(lang='{self.language}', text='{self.text[:50]}...')>"

    def __str__(self):
        return f"Narrative lang='{self.language}', text='{self.text[:50]}...'"
