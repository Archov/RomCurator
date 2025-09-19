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
    """
    Return the default ingestion settings dictionary used by importer workflows.
    
    The returned mapping contains configuration keys consumed by the ingestion pipeline:
    - library_roots (list[str]): initial library root paths (empty by default).
    - batch_size (int): number of files to process per batch.
    - enable_validation (bool): whether to perform file/metadata validation.
    - enable_archive_expansion (bool): whether to expand archive files for inspection.
    - hash_algorithms (list[str]): ordered list of checksum algorithms to compute.
    - file_extensions (dict): two lists under "rom" and "archive" describing recognized file extensions.
    - max_file_size_mb (int): maximum file size in megabytes to consider for ingestion.
    - exclude_patterns (list[str]): glob patterns for files to ignore.
    - enable_platform_detection (bool): whether to attempt platform detection for ROMs.
    - enable_metadata_extraction (bool): whether to extract embedded metadata during ingestion.
    
    Returns:
        dict: A JSON-serializable dictionary with the keys above and their default values.
    """

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
        """
        Validate and normalize a log level value.
        
        Converts the input to an uppercase string and ensures it is one of:
        "DEBUG", "INFO", "WARNING", "ERROR", or "CRITICAL". Returns the normalized
        uppercase log level.
        
        Parameters:
            value (Any): Input value representing a log level (e.g., "info", "Info", or "INFO").
        
        Returns:
            str: Uppercase validated log level.
        
        Raises:
            ValueError: If the value is not one of the allowed log levels.
        """
        level = str(value).upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Log level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return level

    @field_validator("database_path", "importer_scripts_directory", "log_directory", mode="before")
    @classmethod
    def _expand_path(cls, value: Any) -> Path:
        """Ensure a value is returned as a pathlib.Path with user home expansion.

        If the input is already a Path, it is returned with the user home (~) resolved.
        Otherwise, the value is coerced to a string, converted to a Path, and expanded.

        Parameters:
            value (Any): The input value to be converted to an expanded Path.

        Returns:
            Path: An expanded and resolved pathlib.Path instance.
        """
        if isinstance(value, Path):
            return value.expanduser()
        return Path(str(value)).expanduser()

    @field_validator("database_path", mode="after")
    @classmethod
    def _validate_database_path(cls, value: Path, info) -> Path:
        """
        Validate that the parent directory of the provided database path exists unless automatic directory creation is allowed.
        
        This validator reads `auto_create_directories` from the model input (via `info.data`). If `auto_create_directories` is False and the database path's parent directory does not exist, a ValueError is raised to prevent using a non-existent directory. Returns the original Path on success.
        
        Parameters:
            value (Path): The database path being validated.
            info (ValidationInfo): Pydantic validator info object providing access to other field values.
        
        Returns:
            Path: The validated database path.
        
        Raises:
            ValueError: If the parent directory does not exist and `auto_create_directories` is False.
        """
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
        """
        Validate a directory Path against the `auto_create_directories` setting.
        
        Checks the provided Path exists when `auto_create_directories` is False; if the directory does not exist in that case a ValueError is raised. Returns the original Path on success.
        
        Parameters:
            value (Path): The directory path being validated.
            info (ValidationInfo): Pydantic validation context (used to read `auto_create_directories`).
        """
        auto_create = info.data.get("auto_create_directories", True)
        if not auto_create and not value.exists():
            raise ValueError(
                f"Directory '{value}' does not exist and auto creation is disabled."
            )
        return value


class ConfigManager:
    """Centralized configuration management using pydantic models."""

    def __init__(self, config_file: str | Path = "config.json") -> None:
        """
        Initialize ConfigManager.
        
        Loads the configuration from the given JSON file (or creates/resets to defaults if the file is missing or invalid), stores the parsed Pydantic model and a JSON-serializable dict copy, and ensures required directories exist (creating them when permitted by the configuration).
        
        Parameters:
            config_file (str | Path): Path to the configuration file to load. Defaults to "config.json".
        """
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
        """
        Reload the configuration from disk, validate it, update the in-memory model, ensure required directories exist, and return the configuration as a JSON-serializable dict.
        
        This replaces the manager's internal RomCuratorConfig model and its dumped dictionary representation with the contents read from the configured file. If the on-disk file is missing or invalid, the loader may reset the configuration to defaults (and back up the invalid file) according to the manager's recovery policy.
        
        Returns:
            Dict[str, Any]: The reloaded configuration serialized for JSON (suitable for persistence or UI consumption).
        """

        self._config_model = self._load_model()
        self.config = self._config_model.model_dump(mode="json")
        self.ensure_directories()
        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value using a dotted path into the nested config dict.
        
        Key is a dot-separated path (e.g., "gui_settings.theme"). The method traverses nested mappings stored in the manager's internal config and returns the found value. If any path segment is missing or a non-mapping is encountered before the final segment, returns `default`.
        
        Parameters:
            key (str): Dot-separated path to the configuration value.
            default (Any, optional): Value to return if the path does not exist. Defaults to None.
        
        Returns:
            The value at the specified path or `default` if not found.
        """

        keys = key.split(".")
        value: Any = self.config

        for part in keys:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by dotted path and revalidate the in-memory config model.
        
        The `key` is a dotted path (e.g. "ingestion_settings.max_file_size") used to traverse or create nested mappings
        inside the configuration. If any intermediate segment exists but is not a mapping, the update is aborted and an
        error dialog is shown. The provided `value` is applied to the target key, and the resulting configuration is
        validated against RomCuratorConfig.
        
        On successful validation the in-memory Pydantic model is replaced and the JSON-compatible config dict is updated.
        If the model's `auto_create_directories` is enabled, required directories will be created. Validation failures
        or structural conflicts will be reported via an error dialog and logged; the configuration is not changed in those cases.
        
        Parameters:
            key (str): Dotted path to the configuration entry to set.
            value (Any): New value to assign at the specified path.
        
        Side effects:
            - May show GUI error dialogs for validation or structural errors.
            - May create filesystem directories when `auto_create_directories` is True.
            - Updates only the in-memory configuration; does not persist changes to disk (call `save()` to persist).
        """

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
        """
        Validate the in-memory configuration and persist it to the configured file.
        
        If validation fails, the function logs the error, shows a user-facing error dialog
        with formatted validation messages, and aborts without writing to disk. On success
        the validated model is serialized to JSON, required directories are created (if
        auto_create_directories is enabled), and the configuration is written to disk
        using the manager's atomic write procedure.
        """

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
        """
        Ensure required filesystem directories exist.
        
        If the configuration's `auto_create_directories` is True, creates (with parents) the following paths:
        - the parent directory of `database_path`
        - `log_directory`
        - `importer_scripts_directory`
        
        If `auto_create_directories` is False the function returns without action.
        
        On failure to create any directory an error is logged and a user-facing error dialog is shown.
        """

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
        """
        Load and validate the configuration file and return a RomCuratorConfig instance.
        
        If the config file does not exist, is unreadable (I/O or JSON error), or fails model validation,
        this method falls back to application defaults by calling _reset_to_defaults and returns the default model.
        When an unreadable or invalid file is detected the method also logs the problem and triggers a user-facing
        error dialog; invalid files are backed up before defaults are written.
        """

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
        """
        Reset configuration to a fresh default, persist it to disk, and return the new model.
        
        This will:
        - Log the provided reason (and debug-log the optional error).
        - Move any existing config file to a timestamped ".invalid.*" backup (if present).
        - Create a new RomCuratorConfig with default values, write it to the configured config file path, and return it.
        
        Parameters:
            reason (str): Human-readable explanation for why the reset is occurring (logged).
            error (Optional[BaseException]): Optional exception that triggered the reset; included in debug logs.
        
        Returns:
            RomCuratorConfig: The newly created default configuration model that was persisted.
        """

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
        """
        Create a timestamped backup of the existing configuration file by moving it to a new path
        with the pattern "<original_suffix>.invalid.<YYYYMMDDHHMMSS>".
        
        Returns:
            Path: path to the created backup file if the config existed and the move succeeded.
            None: if no config file existed or the backup operation failed.
        """

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
        """
        Serialize the given RomCuratorConfig and atomically write it to the configured file on disk.
        
        The model is converted to a JSON-compatible dict (using Pydantic's `model_dump(mode="json")`), the target directory is created if missing, and the content is written to a temporary file (same suffix plus `.tmp`) before replacing the existing config file to avoid partial writes. Uses UTF-8 encoding and a 4-space indent.
        
        On filesystem errors (OSError) the method logs the exception and shows a configuration error dialog; it does not re-raise the error.
        """

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
        """
        Return a user-facing, multiline string summarizing a Pydantic ValidationError.
        
        The returned message begins with a short header informing the user that the configuration
        contains invalid values and defaults will be used, followed by a bullet list where each
        line describes a single validation issue. Each issue shows the error location (joined
        with " > " for nested fields) when available, then the validation message.
        
        Parameters:
            error (ValidationError): The Pydantic ValidationError to format.
        
        Returns:
            str: A formatted, human-readable error message suitable for display in dialogs or logs.
        """

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
