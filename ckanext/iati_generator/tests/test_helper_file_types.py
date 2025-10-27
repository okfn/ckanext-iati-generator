from ckanext.iati_generator.helpers import iati_file_types
from ckanext.iati_generator.plugin import IatiGeneratorPlugin
from ckanext.iati_generator.models.enums import IATIFileTypes


class TestIatiHelpers:
    def test_iati_file_types_returns_all_enum_values_sorted(self):
        """Should return a list of dicts with value/label for all Enum members, ordered by value."""
        opts = iati_file_types(field=None)

        # 1) count matches the Enum
        assert len(opts) == len(list(IATIFileTypes))

        # 2) values are strings of enum.value and are ordered by int(value)
        values = [o["value"] for o in opts]
        expected_values = [str(e.value) for e in sorted(IATIFileTypes, key=lambda e: e.value)]
        assert values == expected_values

        # 3) labels are name.title() with "_" -> " "
        expected_labels = [e.name.replace("_", " ").title() for e in sorted(IATIFileTypes, key=lambda e: e.value)]
        labels = [o["label"] for o in opts]
        assert labels == expected_labels

    def test_iati_file_types_accepts_field_param(self):
        """Scheming passes 'field'; the helper doesn't use it but must not fail."""
        dummy_field = object()
        opts = iati_file_types(dummy_field)
        assert isinstance(opts, list)
        assert all(isinstance(o, dict) and "value" in o and "label" in o for o in opts)

    def test_plugin_registers_helper_name(self):
        """The plugin should expose the helper under the expected key for Scheming."""
        plugin = IatiGeneratorPlugin()
        helpers = plugin.get_helpers()
        assert "iati_file_type" in helpers
        assert helpers["iati_file_type"] is iati_file_types
