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

 - `iati_namespace`: If you plan to expose more than one IATI file group, define a custom namespace per each IATI file.
   If you plan to have only one IATI file group (organization + activities files), leave this empty
 - `iati_file_type` A selector for the specific IATI file type (e.g., base organization file, names file, org documents file, etc)

### Using the scheming extension

If you are using the `scheming` extension, add this to your schema `yaml` file

```yaml
...

# Section (fieldset) shown on the resource form
resource_form_groups:
  - id: iati
    label:
      en: IATI
      es: IATI
    description:
      en: If this resource must be used to build the final XML IATI file, define how. It's not required to make this dataset public.
      es: Si este recurso debe usarse para construir el archivo IATI XML final, define cómo. No es necesario hacer público este conjunto de datos.

resource_fields:
  ...

  # --- IATI fields ---
  - field_name: iati_namespace
    label:
      en: IATI namespace
      es: Espacio de nombres IATI
    form_group_id: iati
    help_text:
      en: Leave empty for a single IATI file environment.
      es: Dejar vacío para un entorno con un solo archivo IATI.
    form_placeholder: eg. XM-DAC-46002 or my-org
    validators: ignore_missing

  - field_name: iati_file_type
    label:
      en: IATI file type
      es: Tipo de archivo IATI
    form_group_id: iati
    preset: select
    # Helper exposed by this extension that returns [{'value','label'}, ...]
    choices_helper: iati_file_type
    validators: ignore_missing
```

### Without scheming (classic CKAN)

If you are not using the `scheming` extension: **TODO** update the schema manually. We will fix/document this in a future version

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
