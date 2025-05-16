# ckanext-iati-generator

CKAN extension for generating data in IATI format.

### 3. Running tests from inside the container

```bash
# Enter the container
make bash
# Activate the virtual environment
source venv/bin/activate
# Navigate to the extension folder
cd src_extensions/ckanext-iati-generator
# Run the tests
pytest --ckan-ini=test.ini -vv --disable-warnings
```