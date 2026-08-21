"""Tests for the email notification service (mocked SMTP)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "notification"))

from notification import EmailNotifier


@pytest.fixture
def mock_smtp() -> MagicMock:
    """Create a mock SMTP class that tracks sendmail calls."""
    mock = MagicMock()
    instance = MagicMock()
    mock.return_value.__enter__ = MagicMock(return_value=instance)
    mock.return_value.__exit__ = MagicMock(return_value=False)
    mock._instance = instance
    return mock


@pytest.fixture
def notifier(mock_smtp: MagicMock) -> EmailNotifier:
    return EmailNotifier(
        host="smtp.test.com",
        port=465,
        username="test@gmail.com",
        password="secret",
        to_addr="test@gmail.com",
        smtp_class=mock_smtp,
    )


class TestSendCriticalAlerts:
    def test_sends_email_when_critical_alerts_exist(
        self, notifier: EmailNotifier, mock_smtp: MagicMock
    ) -> None:
        aggregated = [
            {"severity": "CRITICAL", "resource": "API", "kind": "TIMEOUT",
             "message": "Slow response", "count": 3, "log_ids": ["l1", "l2"],
             "recurring": True, "repeat_count": 2},
        ]
        severity_counts = {"CRITICAL": 1, "WARNING": 0, "INFO": 0}
        result = notifier.send_critical_alerts(
            aggregated, severity_counts, "2026-08-20T10:00:00Z"
        )
        assert result is True
        mock_smtp._instance.sendmail.assert_called_once()
        call_args = mock_smtp._instance.sendmail.call_args
        assert call_args[0][0] == "test@gmail.com"  # from
        assert call_args[0][1] == "test@gmail.com"  # to

    def test_does_not_send_when_no_critical(
        self, notifier: EmailNotifier, mock_smtp: MagicMock
    ) -> None:
        aggregated = [
            {"severity": "WARNING", "resource": "API", "kind": "TIMEOUT",
             "message": "Slow", "count": 1},
        ]
        severity_counts = {"CRITICAL": 0, "WARNING": 1, "INFO": 0}
        result = notifier.send_critical_alerts(aggregated, severity_counts)
        assert result is False
        mock_smtp._instance.sendmail.assert_not_called()

    def test_does_not_send_when_severity_counts_zero(
        self, notifier: EmailNotifier, mock_smtp: MagicMock
    ) -> None:
        result = notifier.send_critical_alerts([], {"CRITICAL": 0})
        assert result is False

    def test_email_subject_contains_timestamp(
        self, notifier: EmailNotifier, mock_smtp: MagicMock
    ) -> None:
        aggregated = [
            {"severity": "CRITICAL", "resource": "DB", "kind": "DOWN",
             "message": "Connection lost", "count": 1, "log_ids": [],
             "recurring": False, "repeat_count": 0},
        ]
        notifier.send_critical_alerts(
            aggregated, {"CRITICAL": 1, "WARNING": 0, "INFO": 0},
            "2026-08-20T12:00:00Z"
        )
        msg_raw = mock_smtp._instance.sendmail.call_args[0][2]
        import email
        msg_parsed = email.message_from_string(msg_raw)
        payload = msg_parsed.get_payload()
        if isinstance(payload, list):
            body = payload[0].get_payload(decode=True).decode("utf-8")
        else:
            body = payload
        assert "2026-08-20T12:00:00Z" in body
        assert "CRITICAL" in body

    def test_email_body_contains_alert_details(
        self, notifier: EmailNotifier, mock_smtp: MagicMock
    ) -> None:
        aggregated = [
            {"severity": "CRITICAL", "resource": "SF_API", "kind": "AUTH",
             "message": "Token expired", "count": 5,
             "log_ids": ["id1", "id2", "id3"],
             "recurring": True, "repeat_count": 3},
        ]
        notifier.send_critical_alerts(
            aggregated, {"CRITICAL": 1, "WARNING": 0, "INFO": 0}
        )
        body_raw = mock_smtp._instance.sendmail.call_args[0][2]
        import email
        msg = email.message_from_string(body_raw)
        payload = msg.get_payload()
        if isinstance(payload, list):
            body = payload[0].get_payload(decode=True).decode("utf-8")
        else:
            body = payload
        assert "SF_API" in body
        assert "Token expired" in body
        assert "id1, id2, id3" in body

    def test_returns_false_on_smtp_failure(
        self, notifier: EmailNotifier, mock_smtp: MagicMock
    ) -> None:
        mock_smtp._instance.sendmail.side_effect = smtplib.SMTPException("fail")
        aggregated = [
            {"severity": "CRITICAL", "resource": "X", "kind": "Y",
             "message": "Z", "count": 1, "log_ids": [],
             "recurring": False, "repeat_count": 0},
        ]
        result = notifier.send_critical_alerts(
            aggregated, {"CRITICAL": 1, "WARNING": 0, "INFO": 0}
        )
        assert result is False


# Need smtplib for the exception import
import smtplib  # noqa: E402


class TestEnvVars:
    def test_defaults_without_env(self) -> None:
        """Verify default values when no env vars set."""
        import os
        os.environ.pop("SMTP_HOST", None)
        os.environ.pop("SMTP_PORT", None)
        os.environ.pop("SMTP_USERNAME", None)
        os.environ.pop("SMTP_PASSWORD", None)
        os.environ.pop("SMTP_TO", None)
        n = EmailNotifier(smtp_class=MagicMock)
        assert n.host == "smtp.gmail.com"
        assert n.port == 465
        assert n.username == "brunotrolo@gmail.com"

    def test_env_override(self) -> None:
        import os
        os.environ["SMTP_HOST"] = "custom.host.com"
        os.environ["SMTP_PORT"] = "587"
        n = EmailNotifier(smtp_class=MagicMock)
        assert n.host == "custom.host.com"
        assert n.port == 587
        os.environ.pop("SMTP_HOST")
        os.environ.pop("SMTP_PORT")
