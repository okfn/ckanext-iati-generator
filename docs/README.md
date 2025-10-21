# Extended documentation

# IATI Actions Chaining and Overrides

## Description

This document describes how the IATI generation pipeline is organized, which actions compose it, and how to override or chain those actions from another CKAN extension.

## Pipeline: overview

The pipeline is divided into two chainable, side-effect-free actions:

- `iati_csv_to_activities`: reads and validates a CKAN CSV resource and returns IATI activities in memory.
- `iati_activities_to_xml`: converts those activities into the final XML string.

The high-level action `generate_iati_xml` orchestrates both steps using `toolkit.get_action`, allowing chaining or overrides from other extensions.

## How to override / chain actions

To override an action from another extension implement `IActions` and return the same action name. Example:

```python
from ckan import plugins as p
from ckan.plugins import toolkit

class MyIatiOverrides(p.SingletonPlugin):
    p.implements(p.IActions)

    def get_actions(self):
        return {
            "iati_csv_to_activities": self._preprocess_csv,
            # or "iati_activities_to_xml": self._postprocess_xml
        }

    @toolkit.side_effect_free
    def _preprocess_csv(self, context, data_dict):
        # Call base behavior (if an alias "..._original" was registered)
        base = toolkit.get_action("iati_csv_to_activities_original")(context, data_dict)
        acts = base.get("activities", [])
        logs = list(base.get("logs", []))

        # Example enrichment:
        for a in acts:
            # a may be a dict or an object; adapt according to implementation
            reporting = a.get("reporting_org") if isinstance(a, dict) else getattr(a, "reporting_org", None)
            ref = reporting.get("ref") if isinstance(reporting, dict) else getattr(reporting, "ref", None)
            if not ref:
                logs.append("Filled default reporting_org.ref = XM-DAC-XXXX")
                # To mutate: if isinstance(a, dict): a["reporting_org"]["ref"] = "XM-DAC-XXXX"
                # or: setattr(a.reporting_org, "ref", "XM-DAC-XXXX")

        return {"activities": acts, "logs": logs, "resource_name": base.get("resource_name"), "error": None}
```

Notes:
- Both steps are safe to override because they are marked with `@side_effect_free`.
- Using an alias like `iati_csv_to_activities_original` is optional but useful for "wrap" patterns.

## Best practices

- Keep actions declared as side-effect-free if they perform no I/O or persistent changes.
- Respect the return contract: a dict with keys like `activities`, `logs`, `resource_name`, `error`.
- Define authorizations appropriately for each action (read actions in "allow").

## Quick test (suggestion)

You can test an override by injecting an action that adds a log and verifying that `generate_iati_xml` propagates it. Example with pytest/monkeypatch:

```python
def test_generate_iati_xml_propagates_logs(monkeypatch):
    def fake_iati_csv_to_activities(context, data_dict):
        return {"activities": [], "logs": ["from-fake"], "resource_name": "r", "error": None}

    monkeypatch.setattr(toolkit, "get_action", lambda name: fake_iati_csv_to_activities if name == "iati_csv_to_activities" else lambda *a, **k: {})

    # Call generate_iati_xml and assert that the log "from-fake" appears in the result
    # result = toolkit.get_action("generate_iati_xml")(context, data_dict)
    # assert "from-fake" in result.get("logs", [])
```

Adjust according to your test environment and how you import/patch `toolkit.get_action`.

## Checklist

- [x] Pipeline split into chainable and overrideable steps.
- [x] `generate_iati_xml` calls the steps via `toolkit.get_action` (allows chaining).
- [x] Authorizations defined for each action (read actions in "allow").
- [x] Returns include `error` and `logs` consistently (facilitates debugging and wrapping).
- [x] Notes for users on how to override.
- [ ] (Optional) `..._original` aliases to facilitate "wrap" patterns.

✅ This implementation fully enables external CKAN extensions to preprocess or postprocess IATI data pipelines safely.
