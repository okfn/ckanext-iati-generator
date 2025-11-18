import factory
from ckan import model
from ckantoolkit.tests import factories
from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes


class IATIFileFactory(factory.Factory):
    class Meta:
        model = IATIFile

    # We do NOT set `id` (Integer PK autoincrement)
    namespace = "iati-xml"
    # accepts int (value) from the Enum
    file_type = IATIFileTypes.ORGANIZATION_MAIN_FILE.value

    # Resource FK: create a resource and use its id (string)
    resource_id = factory.LazyAttribute(lambda _: factories.Resource()["id"])

    # status fields
    is_valid = True
    last_error = None
    last_processed = None
    last_processed_success = None
    # metadata_created / metadata_updated are handled in the DB (server_default)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        obj = target_class(**kwargs)
        model.Session.add(obj)
        model.Session.commit()
        # important in tests: clear scoped session
        model.Session.remove()
        return obj


def create_iati_file(resource_id=None, **kwargs) -> IATIFile:
    """
    Helper to create an IATIFile with optional overrides.
    E.g.: create_iati_file(resource_id=res_id,
    file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE.value, is_valid=False)
    """
    if resource_id is not None:
        kwargs["resource_id"] = resource_id

    # Allow passing the Enum directly
    if "file_type" in kwargs and hasattr(kwargs["file_type"], "value"):
        kwargs["file_type"] = kwargs["file_type"].value

    return IATIFileFactory(**kwargs)
