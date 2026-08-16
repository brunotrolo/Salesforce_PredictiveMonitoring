"""Tests for shared Logger utility."""

import logging

from src.logger import get_logger, setup_logging


class TestLogger:
    def test_setup_logging_runs(self):
        setup_logging()

    def test_get_logger_returns_bound_logger(self):
        setup_logging()
        logger = get_logger("test_service")
        assert logger is not None

    def test_logger_can_log_info(self, caplog):
        setup_logging()
        logger = get_logger("test_info")
        with caplog.at_level(logging.INFO, logger="test_info"):
            logger.info("test_event", service="collector", status="ok", duration_ms=150)
        assert "test_event" in caplog.text or any(
            r.message == "test_event" for r in caplog.records
        )

    def test_logger_can_log_error(self, caplog):
        setup_logging()
        logger = get_logger("test_error")
        with caplog.at_level(logging.ERROR, logger="test_error"):
            logger.error("error_event", error_type="timeout", service="heuristic")
        assert "error_event" in caplog.text or any(
            r.message == "error_event" for r in caplog.records
        )

    def test_logger_json_output_is_valid(self, caplog):
        import json

        setup_logging()
        logger = get_logger("test_json")
        with caplog.at_level(logging.INFO, logger="test_json"):
            logger.info("json_test", key1="value1", key2=42)
        assert len(caplog.records) > 0
        msg = caplog.records[-1].message
        parsed = json.loads(msg)
        assert parsed["event"] == "json_test"
        assert parsed["key1"] == "value1"
        assert parsed["key2"] == 42
