[![Tests CKAN 2.10](https://github.com/okfn/ckanext-iati-generator/workflows/CKAN%202.10%20Tests/badge.svg)](https://github.com/okfn/ckanext-iati-generator/actions)
[![Tests CKAN 2.11](https://github.com/okfn/ckanext-iati-generator/workflows/CKAN%202.11%20Tests/badge.svg)](https://github.com/okfn/ckanext-iati-generator/actions)  

# IATI generator

CKAN extension for generating data in IATI format. It was developed by BCIE (Banco Centroamericano de Integración Económica)
and the Open Knowledge Foundation (OKFN).  

## Use-cases

Useful extension to transform CKAN resources into IATI XML format.

### Sample screenshots

![IATI conversion](/docs/imgs/iati-page.png)


## Requirements

This CKAN extension relies on the `okfn_iati` [Python library](https://github.com/okfn/okfn_iati)

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.10            | Yes           |
| 2.11            | Yes           |


## Config settings

These are the configuration settings that can be set in your `ckan.ini` file:


```
# rows_limit is the maximum number of rows to be processed in a single IATI generation request.
ckanext.iati_generator.rows_limit = 50000 # default is 50000

# max_allowed_failures is the maximum number of failures in rows before canceling the IATI generation request.
ckanext.iati_generator.max_allowed_failures = 10 # default is 10

# hide_tab allows you to hide the IATI tab from the dataset view for all users.
ckanext.iati_generator.hide_tab = true # default is false
```

## Extra fields: Revisar documentacion completa [AQUI](/docs/extra-fields.md)

This extension requires resource extras:

 - `iati_namespace`: If you plan to expose more than one IATI file, define a custom namespace per each IATI file. If you plan to have only one IATI file (this includes organization and activities file), leave this empty
 - `iati_file_type` A selector for the specific IATI file type (e.g., base organization file, names file, org documents file, etc)

If you are not using the `scheming` extendion: TODO update the schema manually. We will fix this in future version

If you are using the `scheming` extnesion, add this to your `yaml` file

```yaml
iati_namespace: ... (complete)

iati_file_type .... (complete)
```

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
