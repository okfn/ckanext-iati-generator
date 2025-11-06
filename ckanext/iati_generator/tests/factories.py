import factory
from ckan import model
from ckan.tests import factories
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
        ft = kwargs.get("file_type")
        if hasattr(ft, "value"):
            kwargs["file_type"] = ft.value

        obj = target_class(**kwargs)
        model.Session.add(obj)
        model.Session.commit()
        # important in tests: clear scoped session
        model.Session.remove()
        return obj


def create_iati_file(**kwargs) -> IATIFile:
    """
    Helper to create an IATIFile with optional overrides.
    E.g.: create_iati_file(file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE.value, is_valid=False)
    """
    # Allow passing the Enum directly
    if "file_type" in kwargs and hasattr(kwargs["file_type"], "value"):
        kwargs["file_type"] = kwargs["file_type"].value
    return IATIFileFactory(**kwargs)
