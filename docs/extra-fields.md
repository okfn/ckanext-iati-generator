## Extra fields

This extension reads two **resource extras** to know how each resource is used in the final IATI XML:

- `iati_namespace` (string, max 90)  
  If you plan to expose more than one IATI file, define a custom namespace per file.  
  If you plan to have only one IATI file (including organisation and activities), leave this empty.

- `iati_file_type` (select)  
  Reference to the IATI file type. Options come from this extension’s enum via a helper.

You can add these fields to the resource form in two ways:

### A) Using `ckanext-scheming` (recommended)

Add a resource form group and the two fields to your YAML:

```yaml
scheming_version: 2
dataset_type: dataset

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
  - field_name: url
    label: URL
    preset: resource_url_upload

  - field_name: name
    label: Name
    form_placeholder: eg. January 2011 Gold Prices

  - field_name: description
    label: Description
    form_snippet: markdown.html
    form_placeholder: Some useful notes about the data

  - field_name: format
    label: Format
    preset: resource_format_autocomplete

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

> The helper `iati_file_type` is exposed by this extension and returns the enum values and labels, so your select stays up to date automatically.  
> Values are stored in `resource.extras['iati_namespace']` and `resource.extras['iati_file_type']`.

### B) Without scheming (classic CKAN)

If you don’t use scheming:

1) Add a template that **extends** CKAN’s resource form and injects the IATI section:

```jinja
{# ckanext/iati_generator/templates/package/snippets/resource_form.html #}
{% ckan_extends %}

{% block metadata_fields %}
  {{ super() }}

  {% set ex = h.extras_as_dict(data.extras) if data and data.extras else {} %}
  {% set ns_val  = ex.get('iati_namespace','') %}
  {% set type_val = ex.get('iati_file_type','') %}

  <section class="module module-narrow">
    <h3 class="module-heading">{{ _("IATI") }}</h3>
    <div class="module-content">
      <p class="help-block">
        {{ _("If this resource must be used to build the final XML IATI file, define how. It's not required to make this dataset public.") }}
      </p>

      <div class="control-group">
        <label class="control-label" for="field-iati-namespace">{{ _("IATI namespace") }}</label>
        <div class="controls">
          <input type="text" id="field-iati-namespace" name="iati_namespace"
                 value="{{ ns_val }}" maxlength="90" class="control-full"
                 placeholder="{{ _('eg. XM-DAC-46002 or my-org') }}">
          <p class="info-block info-block-small"><i class="fa fa-info-circle"></i>
            {{ _("Leave empty for a single IATI file environment.") }}</p>
        </div>
      </div>

      <div class="control-group">
        <label class="control-label" for="field-iati-file-type">{{ _("IATI file type") }}</label>
        <div class="controls">
          {% set opts = h.iati_file_type() or [] %}
          <select id="field-iati-file-type" name="iati_file_type" class="control-medium">
            <option value="">{{ _("- Select -") }}</option>
            {% for o in opts %}
              <option value="{{ o.value }}" {% if o.value == type_val %}selected{% endif %}>{{ o.text }}</option>
            {% endfor %}
          </select>
          <p class="info-block info-block-small"><i class="fa fa-info-circle"></i>
            {{ _("Choose the reference from the IATI enums list.") }}</p>
        </div>
      </div>
    </div>
  </section>
{% endblock %}
```

2) Ensure CKAN accepts the fields on save by extending the **resource schema** in your own plugin (implementing `IDatasetForm`):

```python
def create_package_schema(self):
    schema = super(..., self).create_package_schema()
    schema['resources'].update({
        'iati_namespace':  [toolkit.get_validator('ignore_missing')],
        'iati_file_type':  [toolkit.get_validator('ignore_missing')],
    })
    return schema

# same for update_package_schema() and show_package_schema()
```

### Translations

All UI strings are wrapped with `_()` and can be localized. Provide at least Spanish entries in your `.po`:

```po
msgid "IATI"
msgstr "IATI"

msgid "If this resource must be used to build the final XML IATI file, define how. It's not required to make this dataset public."
msgstr "Si este recurso debe usarse para construir el archivo IATI XML final, define cómo. No es necesario hacer público este conjunto de datos."

msgid "IATI namespace"
msgstr "Espacio de nombres IATI"

msgid "Leave empty for a single IATI file environment."
msgstr "Dejar vacío para un entorno con un solo archivo IATI."

msgid "IATI file type"
msgstr "Tipo de archivo IATI"

msgid "- Select -"
msgstr "- Seleccionar -"

msgid "Choose the reference from the IATI enums list."
msgstr "Elige la referencia de la lista de enums de IATI."

msgid "eg. XM-DAC-46002 or my-org"
msgstr "ej. XM-DAC-46002 o mi-organización"
```
