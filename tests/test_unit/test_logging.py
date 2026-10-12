import importlib
import logging
from pathlib import Path

app_logger = importlib.import_module("core.logger")


def test_logging_creates_parent_directory_for_file_handler(tmp_path, monkeypatch):
    log_path = tmp_path / "nested" / "bot_errors.log"
    monkeypatch.setattr(app_logger.settings, "LOG_FILE_PATH", str(log_path))
    root_logger = logging.getLogger()
    existing_handlers = root_logger.handlers[:]

    try:
        app_logger.setup_logging()

        assert log_path.parent.is_dir()
        assert any(isinstance(handler, logging.FileHandler) for handler in root_logger.handlers)
    finally:
        for handler in root_logger.handlers[:]:
            handler.close()
        root_logger.handlers[:] = existing_handlers


def test_logging_falls_back_to_temp_directory_when_primary_path_is_unwritable(
    tmp_path, monkeypatch
):
    primary_path = tmp_path / "unwritable" / "bot_errors.log"
    fallback_path = tmp_path / primary_path.name
    monkeypatch.setattr(app_logger.settings, "LOG_FILE_PATH", str(primary_path))
    monkeypatch.setattr(app_logger.tempfile, "gettempdir", lambda: str(tmp_path))
    original_file_handler = app_logger.logging.FileHandler

    def reject_primary_path(path, *args, **kwargs):
        if Path(path) == primary_path:
            raise PermissionError("simulated read-only log directory")
        return original_file_handler(path, *args, **kwargs)

    monkeypatch.setattr(app_logger.logging, "FileHandler", reject_primary_path)
    root_logger = logging.getLogger()
    existing_handlers = root_logger.handlers[:]

    try:
        app_logger.setup_logging()

        assert fallback_path.is_file()
        assert any(isinstance(handler, original_file_handler) for handler in root_logger.handlers)
    finally:
        for handler in root_logger.handlers[:]:
            handler.close()
        root_logger.handlers[:] = existing_handlers
