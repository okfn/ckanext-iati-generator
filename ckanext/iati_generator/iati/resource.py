import logging
import requests
from ckan.plugins import toolkit


log = logging.getLogger(__name__)


def save_resource_data(resource_id, destination_path=None):
    """
    Fetch the data from the CKAN resource.
    This is a placeholder function. The actual implementation will depend on how
    CKAN resources are accessed in your environment.

    :param resource_id: The ID of the CKAN resource to fetch.
    :destination_path: Optional path to save the fetched data.
    """
    log.info(f"Fetching data for resource ID: {resource_id}")
    try:
        resource = toolkit.get_action('resource_show')(
            context={'ignore_auth': True},
            data_dict={'id': resource_id}
        )
    except toolkit.ObjectNotFound:
        log.error(f"Resource with ID {resource_id} not found.")
        return None

    download_url = resource.get('url')
    if not download_url:
        log.error(f"No URL found for resource ID: {resource_id}")
        return None

    file_extension = resource.get('format', '').lower()
    if file_extension not in ['csv']:
        log.error(f"Unsupported file format '{file_extension}' for resource ID: {resource_id}")
        return None

    response = requests.get(download_url)
    if response.status_code != 200:
        log.error(f"Failed to fetch resource data from {download_url}. Status code: {response.status_code}")
        return None

    log.info(f"Successfully fetched data for resource ID: {resource_id}")
    if not destination_path.endswith('.csv'):
        destination_path += '.csv'

    if destination_path:
        with open(destination_path, 'wb') as f:
            f.write(response.content)
        log.info(f"Fetched data saved to {destination_path}")

    log.info(f"Saved data length: {len(response.content)} bytes")
    return destination_path
