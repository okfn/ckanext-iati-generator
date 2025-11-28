# IATI Sample Data Loader

This directory contains scripts to automate the loading of IATI sample data into CKAN for testing the `ckanext-iati-generator` extension.

## Overview

The `seed_iati_integration_data.py` script automates the process of:

1. **Downloading CSV files** from public URLs (GitHub repositories)
2. **Creating CKAN datasets** with proper IATI configuration
3. **Uploading CSV files** as CKAN resources
4. **Creating IATIFile records** to link resources with IATI metadata (namespace, file_type)

This allows you to quickly replicate test scenarios without manual data entry.

## Requirements

- Python 3.7+
- CKAN environment activated
- `pyyaml` and `requests` packages installed
- `ckanext-iati-generator` extension enabled

Install additional requirements:

```bash
pip install pyyaml requests
```

## Configuration

The script uses `sample_data_config.yaml` to define:

- **Organizations**: World Bank, Asian Development Bank, etc.
- **Datasets**: Metadata for each organization's dataset
- **Resources**: CSV files with their URLs and IATI file types
- **Namespaces**: To keep different organization data separate

### Example Configuration Structure

```yaml
organizations:
  world-bank:
    title: "World Bank IATI Data 2024"
    namespace: "iati-xml"
    dataset:
      name: "world-bank-iati-2024"
      title: "World Bank IATI Organization Data 2024"
      # ... more dataset fields
    resources:
      - name: "organization.csv"
        url: "https://..."
        file_type: "ORGANIZATION_MAIN_FILE"
      # ... more resources
```

## Usage

### Setup

**Important**: You must set the `CKAN_INI` environment variable before running the script:

```bash
# In your Docker dev environment
export CKAN_INI=/app/ckan.ini

# Or in a standard CKAN installation
export CKAN_INI=/etc/ckan/default/ckan.ini
```

### Basic Usage

Load all organizations (World Bank + Asian Bank):

```bash
python scripts/seed_iati_integration_data.py
```

Load specific organization:

```bash
# Load World Bank data only
python scripts/seed_iati_integration_data.py --organization world-bank

# Load Asian Development Bank data only
python scripts/seed_iati_integration_data.py --organization asian-bank
```

### Dry Run

See what would be loaded without actually executing:

```bash
python scripts/seed_iati_integration_data.py --dry-run
```

This is useful to:
- Validate your configuration file
- Check URLs before downloading
- Preview what datasets/resources would be created

### Verbose Output

Get detailed logging for debugging:

```bash
python scripts/seed_iati_integration_data.py --verbose
```

### Custom Configuration

Use a different configuration file:

```bash
python scripts/seed_iati_integration_data.py --config my_custom_config.yaml
```

## Complete Examples

### Test 1: Load World Bank Data

```bash
# 1. Activate CKAN environment (if not in Docker)
source /path/to/ckan/bin/activate

# 2. Set CKAN_INI
export CKAN_INI=/app/ckan.ini  # Adjust path as needed

# 3. Navigate to the extension directory
cd /path/to/ckanext-iati-generator

# 4. Load World Bank data
python scripts/seed_iati_integration_data.py --organization world-bank

# 5. Check the results
# Visit: http://your-ckan-instance/ckan-admin/list-iati-files/iati-files
```

### In Docker Environment

```bash
# Enter the CKAN container
make bash

# Set environment variable
source venv/bin/activate
export CKAN_INI=/app/ckan.ini  # o /app/src_extensions/ckanext-iati-generator/test.ini

# Navigate to extension
cd src_extensions/ckanext-iati-generator

# Run the script
python scripts/seed_iati_integration_data.py --organization all --verbose
```

### Test 2: Load Asian Bank with Different Namespace

```bash
# Load Asian Development Bank data (uses "asian-bank" namespace)
python scripts/seed_iati_integration_data.py --organization asian-bank
```

### Test 3: Load Both Organizations

```bash
# Load all sample data
python scripts/seed_iati_integration_data.py --organization all --verbose
```

## Output and Verification

After running the script, you'll see:

```
============================================================
Loading data for: World Bank IATI Data 2024
============================================================

INFO - Creating/updating dataset: world-bank-iati-2024
INFO - Downloading: https://raw.githubusercontent.com/...
INFO - Creating resource: organization.csv
INFO - Creating IATIFile record for resource abc123...
...

============================================================
SUMMARY
============================================================
Datasets created/updated: 2
Resources created: 16
IATIFile records created: 16
Errors: 0
============================================================
```

### Verify the Data

1. **View all IATI files**:
   ```
   http://your-ckan-instance/ckan-admin/list-iati-files/iati-files
   ```

2. **Check datasets**:
   ```
   http://your-ckan-instance/dataset/world-bank-iati-2024
   http://your-ckan-instance/dataset/asian-dev-bank-iati
   ```

3. **Verify namespaces don't mix**:
   - World Bank resources should have namespace: `iati-xml`
   - Asian Bank resources should have namespace: `asian-bank`

## Troubleshooting

### Import Error: "This script must be run in a CKAN environment"

**Solution**: Activate your CKAN virtual environment first:

```bash
source /path/to/ckan/bin/activate
```

### Download Failed

**Problem**: URLs return 404 or connection timeout

**Solutions**:
- Check if the URLs in `sample_data_config.yaml` are correct
- Verify your internet connection
- Try accessing the URL in a browser to confirm it's available
- Check GitHub rate limiting (wait a few minutes if needed)

### Dataset Creation Failed

**Problem**: Permission denied or dataset already exists

**Solutions**:
- Ensure you're running as a sysadmin user
- Check the `owner_org` field in configuration (commented by default)
- If dataset exists and you want to update it, that's normal - the script will update instead

### IATIFile Creation Failed

**Problem**: Invalid file_type

**Solutions**:
- Verify the `file_type` in your config matches an enum in `IATIFileTypes`
- Check `ckanext/iati_generator/models/enums.py` for valid types
- Use the exact enum name (e.g., `ORGANIZATION_MAIN_FILE`)

### Missing File Types

If you need a file type that doesn't exist in `IATIFileTypes`:

1. Add it to `ckanext/iati_generator/models/enums.py`
2. Create a migration to update the database enum
3. Update `sample_data_config.yaml` to use the new type

## Advanced Usage

### Creating Your Own Configuration

1. Copy `sample_data_config.yaml` to a new file:
   ```bash
   cp scripts/sample_data_config.yaml scripts/my_org_config.yaml
   ```

2. Edit the new file:
   ```yaml
   organizations:
     my-organization:
       title: "My Organization IATI Data"
       namespace: "my-org"
       dataset:
         name: "my-org-iati-data"
         title: "My Organization IATI Data"
         notes: "Description here"
       resources:
         - name: "organization.csv"
           url: "https://example.com/data/organization.csv"
           file_type: "ORGANIZATION_MAIN_FILE"
   ```

3. Run with your configuration:
   ```bash
   python scripts/seed_iati_integration_data.py --config scripts/my_org_config.yaml
   ```

### Integrating with CI/CD

Add to your test workflow:

```bash
# In your CI script
source /path/to/ckan/bin/activate
python scripts/seed_iati_integration_data.py --organization all
pytest ckanext/iati_generator/tests/
```

## Script Architecture

### Main Components

1. **IATIDataLoader**: Main class that orchestrates the loading process
2. **download_csv_from_url()**: Downloads CSV files from URLs
3. **create_or_update_dataset()**: Creates or updates CKAN datasets
4. **create_resource_with_csv()**: Uploads CSV files as resources
5. **create_iati_file_record()**: Links resources to IATIFile records

### Flow

```
Config File → IATIDataLoader → For each organization:
    1. Create/update dataset
    2. For each resource:
        a. Download CSV from URL
        b. Upload as CKAN resource
        c. Create IATIFile record
    3. Print summary
```

## Contributing

To add support for more organizations:

1. Find their CSV files (must be publicly accessible URLs)
2. Add configuration to `sample_data_config.yaml`
3. Update the `--organization` choices in `seed_iati_integration_data.py`
4. Test with `--dry-run` first
5. Document any special requirements

## License

This script is part of `ckanext-iati-generator` and follows the same license.

## Support

For issues or questions:
- Check this README first
- Review error messages carefully
- Check CKAN logs: `/var/log/ckan/`
- Open an issue on GitHub with full error details
