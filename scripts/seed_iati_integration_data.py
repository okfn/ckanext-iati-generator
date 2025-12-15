#!/usr/bin/env python
"""
Script to load IATI sample data into CKAN using the CKAN HTTP API.

This script automates the process of:
1. Downloading CSV files from public URLs (GitHub, etc.)
2. Creating CKAN datasets with proper configuration
3. Uploading CSV files as CKAN resources
4. Creating IATIFile records to link resources with IATI metadata

It works against ANY CKAN instance that exposes the API and has the
ckanext-iati-generator extension enabled.

Usage examples:

    python seed_iati_integration_data.py \
        --ckan-url http://localhost:5000 \
        --api-key XXXXX \
        --organization world-bank

    python seed_iati_integration_data.py \
        --ckan-url https://datosabiertos.bcie.org \
        --api-key XXXXX \
        --organization asian-bank --verbose

Environment variables:

    CKAN_URL      (optional, default: http://localhost:5000)
    CKAN_API_KEY  (optional, if not set you must pass --api-key)
"""

import argparse
import logging
import os
import sys

from io import BytesIO
from pathlib import Path
from typing import Dict, Optional
from ckanext.iati_generator.models.enums import IATIFileTypes


import requests
import yaml


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CKANAPIError(Exception):
    """Generic error when calling CKAN API."""

    def __init__(self, message: str, payload: Optional[dict] = None):
        super().__init__(message)
        self.payload = payload or {}


class IATIDataLoader:
    """Main class for loading IATI sample data into CKAN via API."""

    def __init__(
        self,
        ckan_url: str,
        api_key: str,
        config_path: str,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the data loader.

        Args:
            ckan_url: Base URL of the CKAN instance (e.g. http://localhost:5000)
            api_key: CKAN API key (sysadmin or user with enough permissions)
            config_path: Path to the YAML configuration file
            dry_run: If True, show what would be done without executing
            verbose: If True, show detailed logging
        """
        self.ckan_url = ckan_url.rstrip("/")
        self.api_key = api_key
        self.config_path = config_path
        self.dry_run = dry_run
        self.verbose = verbose

        if verbose:
            logger.setLevel(logging.DEBUG)

        self._json_headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        self._default_headers = {"Authorization": self.api_key}

        self.config = self._load_config()
        self.stats = {
            "datasets_created": 0,
            "resources_created": 0,
            "iati_files_created": 0,
            "errors": [],
        }

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------
    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            sys.exit(1)

    # ------------------------------------------------------------------
    # CKAN API helpers
    # ------------------------------------------------------------------
    def _api_url(self, action: str) -> str:
        return f"{self.ckan_url}/api/3/action/{action}"

    def _post_json(self, action: str, data: dict) -> dict:
        """POST to CKAN API with JSON payload and return 'result'."""
        url = self._api_url(action)
        logger.debug("POST %s payload=%r", url, data)
        response = requests.post(url, headers=self._json_headers, json=data, timeout=60)

        if response.status_code != 200:
            raise CKANAPIError(
                f"HTTP {response.status_code} calling {action}", {"response": response.text}
            )

        payload = response.json()
        if not payload.get("success"):
            raise CKANAPIError(
                f"CKAN API {action} failed", payload.get("error") or payload
            )

        return payload["result"]

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------
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
                logger.info("[DRY RUN] Would download from: %s", url)
                return BytesIO(b"dummy,data\n1,2")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            logger.debug("Downloaded %d bytes", len(response.content))
            return BytesIO(response.content)

        except requests.exceptions.RequestException as e:
            logger.error("Failed to download %s: %s", url, e)
            self.stats["errors"].append(f"Download failed: {url}")
            return None

    # ------------------------------------------------------------------
    # Dataset helpers
    # ------------------------------------------------------------------
    def _get_dataset_by_name(self, dataset_name: str) -> Optional[dict]:
        """Return existing dataset (dict) or None if it does not exist."""
        try:
            return self._post_json("package_show", {"id": dataset_name})
        except CKANAPIError as e:
            # Typical CKAN "not found" structure
            error = e.payload or {}
            if error.get("__type") == "Not Found Error":
                logger.debug("Dataset %s not found (will be created)", dataset_name)
                return None
            # Some instances use a different error format
            if "Not found" in str(error) or "NotFound" in str(error):
                logger.debug("Dataset %s not found (will be created)", dataset_name)
                return None
            # Real error
            raise

    def create_or_update_dataset(self, dataset_config: Dict) -> Optional[str]:
        """
        Create or update a CKAN dataset via API.

        Args:
            dataset_config: Dictionary with dataset configuration

        Returns:
            Dataset ID if successful, None otherwise
        """
        try:
            dataset_name = dataset_config["name"]
            logger.info("Creating/updating dataset: %s", dataset_name)

            if self.dry_run:
                logger.info("[DRY RUN] Would create/update dataset: %s", dataset_name)
                self.stats["datasets_created"] += 1
                return f"dummy-id-{dataset_name}"

            existing = self._get_dataset_by_name(dataset_name)

            if existing:
                logger.info("Dataset %s already exists, updating…", dataset_name)
                dataset_config = {**existing, **dataset_config, "id": existing["id"]}
                result = self._post_json("package_update", dataset_config)
            else:
                logger.info("Creating new dataset: %s", dataset_name)
                result = self._post_json("package_create", dataset_config)

            self.stats["datasets_created"] += 1
            return result["id"]

        except Exception as e:
            logger.error("Failed to create/update dataset: %s", e)
            self.stats["errors"].append(
                f"Dataset creation failed: {dataset_config.get('name')}"
            )
            return None

    # ------------------------------------------------------------------
    # Resource helpers
    # ------------------------------------------------------------------
    def create_resource_with_csv(
        self,
        package_id: str,
        csv_file: BytesIO,
        resource_config: Dict,
    ) -> Optional[str]:
        """
        Upload a CSV file as a CKAN resource via API.

        Args:
            package_id: The dataset ID to attach the resource to
            csv_file: BytesIO object with CSV content
            resource_config: Dictionary with resource configuration

        Returns:
            Resource ID if successful, None otherwise
        """
        try:
            logger.info("Creating resource: %s", resource_config["name"])

            if self.dry_run:
                logger.info(
                    "[DRY RUN] Would create resource '%s' in package '%s'",
                    resource_config["name"],
                    package_id,
                )
                self.stats["resources_created"] += 1
                return f"dummy-resource-{resource_config['name']}"

            url = self._api_url("resource_create")

            data = {
                "package_id": package_id,
                "name": resource_config["name"],
                "format": resource_config.get("format", "CSV"),
                "description": resource_config.get("description", ""),
            }

            csv_file.seek(0)
            files = {
                "upload": ("data.csv", csv_file, "text/csv"),
            }

            response = requests.post(
                url,
                headers=self._default_headers,
                data=data,
                files=files,
                timeout=120,
            )

            if response.status_code != 200:
                raise CKANAPIError(
                    f"HTTP {response.status_code} calling resource_create",
                    {"response": response.text},
                )

            payload = response.json()
            if not payload.get("success"):
                raise CKANAPIError(
                    "CKAN API resource_create failed",
                    payload.get("error") or payload,
                )

            result = payload["result"]
            self.stats["resources_created"] += 1
            return result["id"]

        except Exception as e:
            logger.error("Failed to create resource: %s", e)
            self.stats["errors"].append(
                f"Resource creation failed: {resource_config.get('name')}"
            )
            return None

    # ------------------------------------------------------------------
    # IATIFile helpers
    # ------------------------------------------------------------------
    def create_iati_file_record(
        self,
        resource_id: str,
        file_type: str,
        namespace: str,
    ) -> bool:
        """
        Create an IATIFile record for a resource via iati_file_create action.

        Args:
            resource_id: The resource ID
            file_type: The IATI file type (enum name or numeric value)
            namespace: The IATI namespace

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Creating IATIFile record for resource %s", resource_id)

            if self.dry_run:
                logger.info("[DRY RUN] Would create IATIFile for %s", resource_id)
                self.stats["iati_files_created"] += 1
                return True

            # Convert file_type string to numeric value if needed
            if isinstance(file_type, str) and not file_type.isdigit():
                try:
                    file_type_value = IATIFileTypes[file_type].value
                except KeyError:
                    raise ValueError(
                        f"Unknown file_type: {file_type}. "
                        f"Valid types: {', '.join(t.name for t in IATIFileTypes)}"
                    )
            else:
                file_type_value = int(file_type)

            payload = {
                "resource_id": resource_id,
                "file_type": file_type_value,
                "namespace": namespace,
            }

            self._post_json("iati_file_create", payload)

            self.stats["iati_files_created"] += 1
            return True

        except Exception as e:
            logger.error("Failed to create IATIFile record: %s", e)
            self.stats["errors"].append(
                f"IATIFile creation failed for resource: {resource_id}"
            )
            return False

    # ------------------------------------------------------------------
    # High-level operations
    # ------------------------------------------------------------------

    def load_organization(self, org_name: str) -> bool:
        """
        Load all data for a specific organization.

        Args:
            org_name: Organization name from config

        Returns:
            True if successful, False otherwise
        """
        if org_name not in self.config.get("organizations", {}):
            msg = f"Organization '{org_name}' not found in configuration"
            logger.error(msg)
            self.stats["errors"].append(msg)
            return False

        org_config = self.config["organizations"][org_name]
        logger.info("\n%s", "=" * 60)
        logger.info("Loading data for: %s", org_config.get("title", org_name))
        logger.info("%s\n", "=" * 60)

        # Create dataset
        dataset_config = org_config["dataset"].copy()
        dataset_id = self.create_or_update_dataset(dataset_config)

        if not dataset_id:
            self.stats["errors"].append(
                f"Failed to create or update dataset for organization: {org_name}"
            )
            return False

        # Load resources
        success = True
        for resource_cfg in org_config.get("resources", []):
            # Download CSV
            csv_file = self.download_csv_from_url(resource_cfg["url"])
            if not csv_file:
                success = False
                continue

            # Create resource
            resource_config = {
                "name": resource_cfg["name"],
                "format": resource_cfg.get("format", "CSV"),
                "description": resource_cfg.get("description", ""),
            }

            resource_id = self.create_resource_with_csv(
                dataset_id,
                csv_file,
                resource_config,
            )

            if not resource_id:
                success = False
                continue

            # Create IATIFile record
            if not self.create_iati_file_record(
                resource_id,
                resource_cfg["file_type"],
                org_config.get("namespace", "iati-xml"),
            ):
                success = False

        return success

    def load_all(self) -> bool:
        """Load data for all organizations in configuration."""
        success = True
        for org_name in self.config.get("organizations", {}).keys():
            if not self.load_organization(org_name):
                success = False
        return success

    def print_summary(self):
        """Print a summary of the loading operation."""
        logger.info("\n%s", "=" * 60)
        logger.info("SUMMARY")
        logger.info("%s", "=" * 60)
        logger.info("Datasets created/updated: %d", self.stats["datasets_created"])
        logger.info("Resources created: %d", self.stats["resources_created"])
        logger.info(
            "IATIFile records created: %d",
            self.stats["iati_files_created"],
        )
        logger.info("Errors: %d", len(self.stats["errors"]))

        if self.stats["errors"]:
            logger.warning("\nErrors encountered:")
            for error in self.stats["errors"]:
                logger.warning("  - %s", error)

        logger.info("%s\n", "=" * 60)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    """Main entry point for the script."""

    default_ckan_url = os.environ.get("CKAN_URL", "http://localhost:5000")
    default_api_key = os.environ.get("CKAN_API_KEY")

    parser = argparse.ArgumentParser(
        description="Load IATI sample data into CKAN via HTTP API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--organization",
        choices=["world-bank", "asian-bank", "all"],
        default="all",
        help="Which organization data to load (default: all)",
    )

    parser.add_argument(
        "--config",
        default=str(Path(__file__).parent / "sample_data_config.yaml"),
        help="Path to configuration file (default: sample_data_config.yaml)",
    )

    parser.add_argument(
        "--ckan-url",
        default=default_ckan_url,
        help=f"Base URL of the CKAN instance (default: {default_ckan_url})",
    )

    parser.add_argument(
        "--api-key",
        default=default_api_key,
        help="CKAN API key. If not provided, CKAN_API_KEY env var must be set.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: CKAN API key is required.")
        print("Pass --api-key or set CKAN_API_KEY environment variable.")
        sys.exit(1)

    # Initialize loader
    loader = IATIDataLoader(
        ckan_url=args.ckan_url,
        api_key=args.api_key,
        config_path=args.config,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    # Load data
    if args.organization == "all":
        success = loader.load_all()
    else:
        success = loader.load_organization(args.organization)

    # Print summary
    loader.print_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
