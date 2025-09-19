"""Configuration management utilities for the ROM Curator application."""

from __future__ import annotations

import json
import logging
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from PyQt5.QtWidgets import QApplication, QMessageBox
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

LOGGER = logging.getLogger(__name__)


def _default_ingestion_settings() -> Dict[str, Any]:
    """Return the default ingestion settings used by the importer workflows."""

    return {
        "library_roots": [],
        "batch_size": 100,
        "enable_validation": True,
        "enable_archive_expansion": True,
        "hash_algorithms": ["sha1", "crc32", "md5", "sha256"],
        "file_extensions": {
            "rom": [
                ".rom",
                ".bin",
                ".smd",
                ".sfc",
                ".nes",
                ".gb",
                ".gba",
                ".nds",
                ".iso",
                ".img",
            ],
            "archive": [".zip", ".7z", ".rar", ".tar", ".gz"],
        },
        "max_file_size_mb": 1024,
        "exclude_patterns": ["*.tmp", "*.temp", "*.bak", "*.backup"],
        "enable_platform_detection": True,
        "enable_metadata_extraction": True,
    }


class GuiSettings(BaseModel):
    """GUI specific configuration."""

    model_config = ConfigDict(extra="allow")

    window_width: int = Field(default=1200, ge=800, le=3840)
    window_height: int = Field(default=800, ge=600, le=2160)
    theme: Literal["dark", "light"] = "dark"


class RomCuratorConfig(BaseModel):
    """Root configuration model."""

    model_config = ConfigDict(extra="allow")

    auto_create_directories: bool = True
    database_path: Path = Field(default=Path("./database/RomCurator.db"))
    importer_scripts_directory: Path = Field(default=Path("./scripts/seeders/"))
    log_directory: Path = Field(default=Path("./logs/"))
    log_level: str = "INFO"
    progress_update_interval: int = Field(default=100, ge=1, le=1000)
    gui_settings: GuiSettings = Field(default_factory=GuiSettings)
    ingestion_settings: Dict[str, Any] = Field(default_factory=_default_ingestion_settings)

    @field_validator("log_level", mode="before")
    @classmethod
    def _validate_log_level(cls, value: Any) -> str:
        level = str(value).upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Log level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return level

    @field_validator("database_path", "importer_scripts_directory", "log_directory", mode="before")
    @classmethod
    def _expand_path(cls, value: Any) -> Path:
        if isinstance(value, Path):
            return value.expanduser()
        return Path(str(value)).expanduser()

    @field_validator("database_path", mode="after")
    @classmethod
    def _validate_database_path(cls, value: Path, info) -> Path:
        parent = value.parent
        auto_create = info.data.get("auto_create_directories", True)
        if not auto_create and not parent.exists():
            raise ValueError(
                f"Database directory '{parent}' does not exist and auto creation is disabled."
            )
        return value

    @field_validator("importer_scripts_directory", "log_directory", mode="after")
    @classmethod
    def _validate_directories(cls, value: Path, info) -> Path:
        auto_create = info.data.get("auto_create_directories", True)
        if not auto_create and not value.exists():
            raise ValueError(
                f"Directory '{value}' does not exist and auto creation is disabled."
            )
        return value


class ConfigManager:
    """Centralized configuration management using pydantic models."""

    def __init__(self, config_file: str | Path = "config.json") -> None:
        self.config_file = Path(config_file)
        self._logger = LOGGER
        self._config_model = self._load_model()
        self.config: Dict[str, Any] = self._config_model.model_dump(mode="json")
        self.ensure_directories()

    @property
    def model(self) -> RomCuratorConfig:
        """Return the typed configuration model."""

        return self._config_model

    def load_config(self) -> Dict[str, Any]:
        """Reload configuration from disk and return it as a dictionary."""

        self._config_model = self._load_model()
        self.config = self._config_model.model_dump(mode="json")
        self.ensure_directories()
        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dotted path."""

        keys = key.split(".")
        value: Any = self.config

        for part in keys:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and revalidate the model."""

        keys = key.split(".")
        updated_config = deepcopy(self.config)
        ref = updated_config

        for part in keys[:-1]:
            if part not in ref:
                ref[part] = {}
            elif not isinstance(ref[part], dict):
                message = f"Cannot set '{key}': '{part}' is not a mapping."
                self._logger.error(message)
                self._show_error_dialog("Invalid Configuration", message)
                return
            ref = ref[part]

        ref[keys[-1]] = value

        try:
            self._config_model = RomCuratorConfig.model_validate(updated_config)
        except ValidationError as error:
            self._logger.exception("Invalid configuration update for '%s'", key)
            self._show_error_dialog(
                "Invalid Configuration",
                self._format_validation_errors(error),
            )
            return

        self.config = self._config_model.model_dump(mode="json")
        if self._config_model.auto_create_directories:
            self.ensure_directories()

    def save(self) -> None:
        """Persist configuration to disk after validation."""

        try:
            self._config_model = RomCuratorConfig.model_validate(self.config)
        except ValidationError as error:
            self._logger.exception("Configuration invalid during save")
            self._show_error_dialog(
                "Invalid Configuration",
                self._format_validation_errors(error),
            )
            return

        self.config = self._config_model.model_dump(mode="json")
        self.ensure_directories()
        self._write_config_file(self._config_model)

    def ensure_directories(self) -> None:
        """Create required directories if they do not exist."""

        if not self._config_model.auto_create_directories:
            return

        directories = [
            self._config_model.database_path.parent,
            self._config_model.log_directory,
            self._config_model.importer_scripts_directory,
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self._logger.exception("Failed to create directory %s", directory)
                self._show_error_dialog(
                    "Directory Creation Failed",
                    f"Unable to create directory '{directory}': {exc}",
                )

    def _load_model(self) -> RomCuratorConfig:
        """Load and validate configuration, falling back to defaults on error."""

        if not self.config_file.exists():
            return self._reset_to_defaults("Configuration file not found. Generating defaults.")

        try:
            with open(self.config_file, "r", encoding="utf-8") as handle:
                raw_config = json.load(handle)
            return RomCuratorConfig.model_validate(raw_config)
        except (json.JSONDecodeError, OSError) as exc:
            self._logger.exception("Failed to read configuration")
            self._show_error_dialog(
                "Configuration Error",
                "The configuration file could not be read. Default settings will be used.",
            )
            return self._reset_to_defaults("Configuration file unreadable. Restoring defaults.", exc)
        except ValidationError as error:
            self._logger.exception("Configuration validation failed")
            self._show_error_dialog(
                "Invalid Configuration",
                self._format_validation_errors(error),
            )
            return self._reset_to_defaults("Configuration validation failed. Restoring defaults.")

    def _reset_to_defaults(self, reason: str, error: Optional[BaseException] = None) -> RomCuratorConfig:
        """Create a fresh default configuration and persist it to disk."""

        self._logger.warning(reason)
        if error is not None:
            self._logger.debug("Resetting configuration due to: %s", error)
        backup_path = self._backup_invalid_config()
        if backup_path is not None:
            self._logger.info("Backed up invalid configuration to %s", backup_path)

        default_model = RomCuratorConfig()
        self._write_config_file(default_model)
        return default_model

    def _backup_invalid_config(self) -> Optional[Path]:
        """Backup the current config file before overwriting defaults."""

        if not self.config_file.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = self.config_file.with_suffix(
            f"{self.config_file.suffix}.invalid.{timestamp}"
        )
        try:
            shutil.move(self.config_file, backup_path)
        except OSError as exc:
            self._logger.warning("Could not back up invalid configuration: %s", exc)
            return None
        return backup_path

    def _write_config_file(self, config_model: RomCuratorConfig) -> None:
        """Write the provided configuration model to disk."""

        data = config_model.model_dump(mode="json")
        try:
            parent = self.config_file.parent
            if parent and not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.config_file.with_suffix(
                f"{self.config_file.suffix}.tmp"
            )
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=4)
            tmp_path.replace(self.config_file)
        except OSError as exc:
            self._logger.exception("Could not save config file")
            self._show_error_dialog(
                "Configuration Error",
                f"Unable to save configuration file: {exc}",
            )

    @staticmethod
    def _show_error_dialog(title: str, message: str) -> None:
        """Display an error dialog if a QApplication is active. Otherwise log the error."""

        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(None, title, message)
        else:
            LOGGER.error("Error dialog: %s - %s", title, message)

    @staticmethod
    def _format_validation_errors(error: ValidationError) -> str:
        """Format validation errors for display."""

        error_lines = [
            "The configuration file contains invalid values. Default settings will be used.",
            "",
        ]

        for detail in error.errors():
            location = " > ".join(str(part) for part in detail.get("loc", ()))
            message = detail.get("msg", "Invalid value")
            if location:
                error_lines.append(f"- {location}: {message}")
            else:
                error_lines.append(f"- {message}")

        return "\n".join(error_lines)


__all__ = [
    "ConfigManager",
    "GuiSettings",
    "RomCuratorConfig",
]
