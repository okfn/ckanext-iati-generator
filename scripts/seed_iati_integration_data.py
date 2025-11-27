#!/usr/bin/env python
"""
Script to load IATI sample data into CKAN.

This script automates the process of:
1. Downloading CSV files from public URLs (GitHub, etc.)
2. Creating CKAN datasets with proper configuration
3. Uploading CSV files as CKAN resources
4. Creating IATIFile records to link resources with IATI metadata

Usage:
    python seed_iati_integration_data.py --organization world-bank
    python seed_iati_integration_data.py --organization asian-bank --namespace asian-bank
    python seed_iati_integration_data.py --organization all
    python seed_iati_integration_data.py --config custom_config.yaml --dry-run
"""

import argparse
import logging
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import requests
from io import BytesIO

# Add parent directory to path to import ckanext modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ckan.cli import load_config as ckan_load_config
    from ckan.config.environment import load_environment
    import ckan.plugins.toolkit as toolkit
    from ckanext.iati_generator.models.enums import IATIFileTypes
except ImportError as e:
    print("Error: This script must be run in a CKAN environment")
    print("Import error:", e)
    print("Try: source /path/to/ckan/bin/activate")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _init_ckan():
    """
    Ensure CKAN environment is loaded using CKAN_INI.
    """
    ini_path = os.environ.get("CKAN_INI")
    if not ini_path:
        print("Please set CKAN_INI, e.g.: export CKAN_INI=/app/ckan.ini")
        sys.exit(1)

    conf = ckan_load_config(ini_path)
    load_environment(conf)


class IATIDataLoader:
    """Main class for loading IATI sample data into CKAN."""
    
    def __init__(self, config_path: str, dry_run: bool = False, verbose: bool = False):
        """
        Initialize the data loader.
        
        Args:
            config_path: Path to the YAML configuration file
            dry_run: If True, show what would be done without executing
            verbose: If True, show detailed logging
        """
        self.config_path = config_path
        self.dry_run = dry_run
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self.config = self._load_config()
        self.stats = {
            'datasets_created': 0,
            'resources_created': 0,
            'iati_files_created': 0,
            'errors': []
        }
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            sys.exit(1)
    
    def download_csv_from_url(self, url: str) -> Optional[BytesIO]:
        """
        Download a CSV file from a public URL.
        
        Args:
            url: The URL to download from
            
        Returns:
            BytesIO object with the file content, or None if download failed
        """
        try:
            logger.info(f"Downloading: {url}")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would download from: {url}")
                return BytesIO(b"dummy,data\n1,2")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            logger.debug(f"Downloaded {len(response.content)} bytes")
            return BytesIO(response.content)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            self.stats['errors'].append(f"Download failed: {url}")
            return None
    
    def create_or_update_dataset(self, dataset_config: Dict) -> Optional[str]:
        """
        Create or update a CKAN dataset.
        
        Args:
            dataset_config: Dictionary with dataset configuration
            
        Returns:
            Dataset ID if successful, None otherwise
        """
        try:
            dataset_name = dataset_config['name']
            logger.info(f"Creating/updating dataset: {dataset_name}")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create dataset: {dataset_name}")
                return f"dummy-id-{dataset_name}"
            
            # Try to get existing dataset
            context = {'user': self._get_site_user()}
            try:
                existing = toolkit.get_action('package_show')(
                    context, {'id': dataset_name}
                )
                logger.info(f"Dataset {dataset_name} already exists, updating...")
                dataset_config['id'] = existing['id']
                result = toolkit.get_action('package_update')(context, dataset_config)
            except toolkit.ObjectNotFound:
                logger.info(f"Creating new dataset: {dataset_name}")
                result = toolkit.get_action('package_create')(context, dataset_config)
            
            self.stats['datasets_created'] += 1
            return result['id']
            
        except Exception as e:
            logger.error(f"Failed to create/update dataset: {e}")
            self.stats['errors'].append(f"Dataset creation failed: {dataset_config.get('name')}")
            return None
    
    def create_resource_with_csv(
        self,
        package_id: str,
        csv_file: BytesIO,
        resource_config: Dict
    ) -> Optional[str]:
        """
        Upload a CSV file as a CKAN resource.
        
        Args:
            package_id: The dataset ID to attach the resource to
            csv_file: BytesIO object with CSV content
            resource_config: Dictionary with resource configuration
            
        Returns:
            Resource ID if successful, None otherwise
        """
        try:
            logger.info(f"Creating resource: {resource_config['name']}")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create resource: {resource_config['name']}")
                return f"dummy-resource-{resource_config['name']}"
            
            context = {'user': self._get_site_user()}
            resource_config['package_id'] = package_id
            resource_config['upload'] = csv_file
            
            result = toolkit.get_action('resource_create')(context, resource_config)
            
            self.stats['resources_created'] += 1
            return result['id']
            
        except Exception as e:
            logger.error(f"Failed to create resource: {e}")
            self.stats['errors'].append(f"Resource creation failed: {resource_config.get('name')}")
            return None
    
    def create_iati_file_record(
        self,
        resource_id: str,
        file_type: str,
        namespace: str
    ) -> bool:
        """
        Create an IATIFile record for a resource.
        
        Args:
            resource_id: The resource ID
            file_type: The IATI file type (enum name or value)
            namespace: The IATI namespace
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Creating IATIFile record for resource {resource_id}")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create IATIFile: type={file_type}, namespace={namespace}")
                return True
            
            # Convert file_type string to enum value if needed
            if isinstance(file_type, str) and not file_type.isdigit():
                file_type_value = IATIFileTypes[file_type].value
            else:
                file_type_value = int(file_type)
            
            context = {'user': self._get_site_user()}
            toolkit.get_action('iati_file_create')(context, {
                'resource_id': resource_id,
                'file_type': file_type_value,
                'namespace': namespace
            })
            
            self.stats['iati_files_created'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to create IATIFile record: {e}")
            self.stats['errors'].append(f"IATIFile creation failed for resource: {resource_id}")
            return False
    
    def _get_site_user(self) -> str:
        """Get the site user for API actions."""
        site_user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        return site_user['name']
    
    def load_organization(self, org_name: str) -> bool:
        """
        Load all data for a specific organization.
        
        Args:
            org_name: Organization name from config
            
        Returns:
            True if successful, False otherwise
        """
        if org_name not in self.config.get('organizations', {}):
            logger.error(f"Organization '{org_name}' not found in configuration")
            return False
        
        org_config = self.config['organizations'][org_name]
        logger.info(f"\n{'='*60}")
        logger.info(f"Loading data for: {org_config.get('title', org_name)}")
        logger.info(f"{'='*60}\n")
        
        # Create dataset
        dataset_config = org_config['dataset'].copy()
        dataset_id = self.create_or_update_dataset(dataset_config)
        
        if not dataset_id:
            return False
        
        # Load resources
        success = True
        for resource_cfg in org_config.get('resources', []):
            # Download CSV
            csv_file = self.download_csv_from_url(resource_cfg['url'])
            if not csv_file:
                success = False
                continue
            
            # Create resource
            resource_config = {
                'name': resource_cfg['name'],
                'format': resource_cfg.get('format', 'CSV'),
                'description': resource_cfg.get('description', ''),
            }
            
            resource_id = self.create_resource_with_csv(
                dataset_id,
                csv_file,
                resource_config
            )
            
            if not resource_id:
                success = False
                continue
            
            # Create IATIFile record
            if not self.create_iati_file_record(
                resource_id,
                resource_cfg['file_type'],
                org_config.get('namespace', 'iati-xml')
            ):
                success = False
        
        return success
    
    def load_all(self) -> bool:
        """Load data for all organizations in configuration."""
        success = True
        for org_name in self.config.get('organizations', {}).keys():
            if not self.load_organization(org_name):
                success = False
        return success
    
    def print_summary(self):
        """Print a summary of the loading operation."""
        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Datasets created/updated: {self.stats['datasets_created']}")
        logger.info(f"Resources created: {self.stats['resources_created']}")
        logger.info(f"IATIFile records created: {self.stats['iati_files_created']}")
        logger.info(f"Errors: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            logger.warning("\nErrors encountered:")
            for error in self.stats['errors']:
                logger.warning(f"  - {error}")
        
        logger.info(f"{'='*60}\n")


def main():
    """Main entry point for the script."""
    _init_ckan()  # <-- antes de crear el loader / usar toolkit
    
    parser = argparse.ArgumentParser(
        description='Load IATI sample data into CKAN',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--organization',
        choices=['world-bank', 'asian-bank', 'all'],
        default='all',
        help='Which organization data to load (default: all)'
    )
    
    parser.add_argument(
        '--config',
        default=str(Path(__file__).parent / 'sample_data_config.yaml'),
        help='Path to configuration file (default: sample_data_config.yaml)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Initialize loader
    loader = IATIDataLoader(
        config_path=args.config,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    # Load data
    if args.organization == 'all':
        success = loader.load_all()
    else:
        success = loader.load_organization(args.organization)
    
    # Print summary
    loader.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
