[![Tests CKAN 2.10](https://github.com/okfn/ckanext-iati-generator/workflows/CKAN%202.10%20Tests/badge.svg)](https://github.com/okfn/ckanext-iati-generator/actions)
[![Tests CKAN 2.11](https://github.com/okfn/ckanext-iati-generator/workflows/CKAN%202.11%20Tests/badge.svg)](https://github.com/okfn/ckanext-iati-generator/actions)
This repository contains a CKAN open-source extension that can be added to any CKAN 2.11+ instance. It was developed by BCIE
(Banco Centroamericano de Integración Económica) and Open Knowledge Foundation (OKFN).  

# IATI generator

CKAN extension for generating data in IATI format.

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
```


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
