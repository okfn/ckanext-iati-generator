import urllib.request

from ckan.plugins import toolkit

from ckanext.iati_generator import helpers


def test_notify_slack_iati_error_sends_request(monkeypatch):
    """Ensures the notification is sent when Slack is enabled and webhook is set."""
    called = {}

    def fake_urlopen(req, timeout=5):
        called["req"] = req

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return DummyResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        toolkit,
        "config",
        {
            "ckanext.iati_generator.slack_enabled": "true",
            "ckanext.iati_generator.slack_webhook_url": "https://example.com/hook",
            "ckan.site_url": "https://ckan.example",
        },
    )

    dataset = {
        "name": "my-dataset",
        "title": "My Dataset",
        "id": "123",
        "iati_namespace": "ns",
    }

    ok = helpers.notify_slack_iati_error("activity", dataset, None)

    assert ok is True
    assert "req" in called


def test_notify_slack_iati_error_disabled_returns_false(monkeypatch):
    """Ensures it returns False when Slack is disabled."""
    monkeypatch.setattr(
        toolkit,
        "config",
        {
            "ckanext.iati_generator.slack_enabled": "false",
            "ckanext.iati_generator.slack_webhook_url": "https://example.com/hook",
        },
    )

    ok = helpers.notify_slack_iati_error("activity", {}, None)
    assert ok is False


def test_notify_slack_iati_error_missing_webhook_returns_false(monkeypatch):
    """Ensures it returns False when the webhook is missing."""
    monkeypatch.setattr(
        toolkit,
        "config",
        {
            "ckanext.iati_generator.slack_enabled": "true",
            "ckanext.iati_generator.slack_webhook_url": "",
        },
    )

    ok = helpers.notify_slack_iati_error("activity", {}, None)
    assert ok is False


def test_notify_slack_iati_error_handles_urlopen_error(monkeypatch):
    """Ensures it returns False when urlopen raises an exception."""
    def fake_urlopen(req, timeout=5):
        raise Exception("boom")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        toolkit,
        "config",
        {
            "ckanext.iati_generator.slack_enabled": "true",
            "ckanext.iati_generator.slack_webhook_url": "https://example.com/hook",
        },
    )

    ok = helpers.notify_slack_iati_error("activity", {}, None)
    assert ok is False


def test_notify_slack_iati_error_disabled_when_blank(monkeypatch):
    """Ensures it returns False when slack_enabled is blank."""
    monkeypatch.setattr(
        toolkit,
        "config",
        {
            "ckanext.iati_generator.slack_enabled": "",
            "ckanext.iati_generator.slack_webhook_url": "https://example.com/hook",
        },
    )

    ok = helpers.notify_slack_iati_error("activity", {}, None)
    assert ok is False


def test_notify_slack_iati_error_payload_includes_details(monkeypatch):
    """Ensures the payload includes dataset and error details."""
    captured = {}

    def fake_urlopen(req, timeout=5):
        captured["body"] = req.data

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return DummyResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        toolkit,
        "config",
        {
            "ckanext.iati_generator.slack_enabled": "true",
            "ckanext.iati_generator.slack_webhook_url": "https://example.com/hook",
            "ckan.site_url": "https://ckan.example",
        },
    )

    dataset = {
        "name": "my-dataset",
        "title": "My Dataset",
        "id": "123",
        "iati_namespace": "ns",
    }
    error_dict = [{"title": "Bad", "details": "oops", "csv_file": "file.csv"}]

    ok = helpers.notify_slack_iati_error("activity", dataset, error_dict)

    assert ok is True
    assert b"My Dataset" in captured["body"]
    assert b"file.csv" in captured["body"]