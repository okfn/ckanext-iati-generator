
import logging
from ckan import plugins as p
from ckan.plugins import toolkit
from flask import Blueprint, Response

# Librería IATI
from okfn_iati import (
    Activity, Narrative, OrganizationRef, IatiXmlGenerator,
    ActivityStatus, OrganisationType, IatiActivities
)

log = logging.getLogger(__name__)


class IatiGeneratorPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "ckanext-iati-generator")

    def get_blueprint(self):
        iati_bp = Blueprint("iati_generator", __name__)

        @iati_bp.route("/iati/generate")
        def generate_iati_xml():
            reporting_org_id = "XM-DAC-12345"
            activity = Activity(
                iati_identifier=f"{reporting_org_id}-TEST001",
                reporting_org=OrganizationRef(
                    ref=reporting_org_id,
                    type=OrganisationType.GOVERNMENT.value,
                    narratives=[Narrative(text="Example Organization")]
                ),
                title=[Narrative(text="Sample Project")],
                activity_status=ActivityStatus.IMPLEMENTATION,
            )

            iati_activities = IatiActivities(
                version="2.03",
                activities=[activity]
            )

            generator = IatiXmlGenerator()
            xml_string = generator.generate_iati_activities_xml(iati_activities)

            return Response(xml_string, mimetype="application/xml")

        return iati_bp
