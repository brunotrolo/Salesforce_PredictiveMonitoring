"""Email notification service for critical alerts.

Sends email alerts via SMTP (Gmail) when CRITICAL alerts are aggregated.
Uses stdlib smtplib — no external dependencies.

Environment variables:
    SMTP_HOST     — SMTP server (default: smtp.gmail.com)
    SMTP_PORT     — SMTP port (default: 465, SSL)
    SMTP_USERNAME — sender email (default: brunotrolo@gmail.com)
    SMTP_PASSWORD — app password (required for production)
    SMTP_TO       — recipient email (default: brunotrolo@gmail.com)
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

_DEFAULT_HOST = "smtp.gmail.com"
_DEFAULT_PORT = 465
_DEFAULT_FROM = "brunotrolo@gmail.com"
_DEFAULT_TO = "brunotrolo@gmail.com"


class EmailNotifier:
    """Send email notifications for CRITICAL alerts.

    In production, reads SMTP config from env vars.  Accepts a custom
    ``smtp_class`` parameter for testability (mock SMTP injection).
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        to_addr: str | None = None,
        smtp_class: type | None = None,
    ) -> None:
        self.host = host or os.environ.get("SMTP_HOST", _DEFAULT_HOST)
        self.port = port or int(os.environ.get("SMTP_PORT", str(_DEFAULT_PORT)))
        self.username = username or os.environ.get("SMTP_USERNAME", _DEFAULT_FROM)
        self.password = password or os.environ.get("SMTP_PASSWORD", "")
        self.to_addr = to_addr or os.environ.get("SMTP_TO", _DEFAULT_TO)
        self._smtp_class = smtp_class or smtplib.SMTP_SSL

    def send_critical_alerts(
        self,
        aggregated: list[dict[str, Any]],
        severity_counts: dict[str, int],
        snapshot_timestamp: str = "",
    ) -> bool:
        """Send email if any CRITICAL alerts exist.

        Returns True if email was sent successfully, False otherwise.
        Does NOT raise on failure — observational step.
        """
        critical_count = severity_counts.get("CRITICAL", 0)
        if critical_count == 0:
            return False

        critical_alerts = [a for a in aggregated if a.get("severity") == "CRITICAL"]
        if not critical_alerts:
            return False

        subject = (
            f"[Salesforce Monitor] {critical_count} alerta(s) CRITICAL "
            f"- {snapshot_timestamp}"
        )
        body = self._build_body(critical_alerts, severity_counts, snapshot_timestamp)
        return self._send_email(subject, body)

    def _build_body(
        self,
        critical_alerts: list[dict[str, Any]],
        severity_counts: dict[str, int],
        timestamp: str,
    ) -> str:
        lines = [
            "Salesforce Predictive Monitoring - Alertas CRITICAL",
            f"Timestamp: {timestamp}",
            "",
            f"Resumo: {severity_counts.get('CRITICAL', 0)} CRITICAL, "
            f"{severity_counts.get('WARNING', 0)} WARNING, "
            f"{severity_counts.get('INFO', 0)} INFO",
            "",
            "--- Detalhes dos alertas CRITICAL ---",
            "",
        ]
        for alert in critical_alerts:
            lines.append(f"Recurso: {alert.get('resource', 'unknown')}")
            lines.append(f"Tipo: {alert.get('kind', 'unknown')}")
            lines.append(f"Mensagem: {alert.get('message', '')}")
            lines.append(f"Contagem: {alert.get('count', 1)}")
            if alert.get("recurring"):
                lines.append(f"Recorrencia: {alert.get('repeat_count', 0)}x")
            log_ids = alert.get("log_ids", [])
            if log_ids:
                lines.append(f"Log IDs: {', '.join(log_ids[:5])}")
            lines.append("")

        lines.append("--- Fim ---")
        lines.append("")
        lines.append("Este email foi gerado automaticamente pelo Salesforce Monitor.")
        return "\n".join(lines)

    def _send_email(self, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.username
            msg["To"] = self.to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            context = ssl.create_default_context()
            with self._smtp_class(self.host, self.port, context=context) as server:
                server.login(self.username, self.password)
                server.sendmail(self.username, self.to_addr, msg.as_string())
            return True
        except Exception:
            return False
