"""
Configuration Drift Detection Test

This test ensures that all settings in omega_kg.settings.Settings
match the .env.example file, preventing configuration drift.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Set, Tuple

import pytest

# Configure logging for better debugging
logger = logging.getLogger(__name__)


# Set required environment variables before importing Settings
# to prevent validation errors during module import
os.environ.setdefault("NEO4J_PASSWORD", "test-password")
os.environ.setdefault("LINEAR_WEBHOOK_SECRET", "test-secret")

from omega_kg.settings import Settings  # noqa: E402


class ConfigDriftError(Exception):
    """Custom exception for configuration drift issues."""

    pass


def parse_env_example() -> Set[str]:
    """
    Parse .env.example and extract all non-comment, non-empty keys.

    Returns:
        Set of environment variable keys found in .env.example

    Raises:
        FileNotFoundError: If .env.example file doesn't exist
        PermissionError: If unable to read the file
        ValueError: If file contains malformed entries
    """
    env_example_path = Path(__file__).parent.parent / ".env.example"

    if not env_example_path.exists():
        raise FileNotFoundError(f".env.example not found at {env_example_path}")

    if not env_example_path.is_file():
        raise ValueError(f"Expected file at {env_example_path}, found directory")

    keys = set()
    line_number = 0

    try:
        with open(env_example_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Extract key before '=' sign
                if "=" in line:
                    try:
                        key = line.split("=", 1)[0].strip()
                        # Accept all uppercase keys (with or without underscore)
                        if key and key.isupper():
                            keys.add(key)
                        elif key:
                            logger.warning(
                                f"Line {line_number}: Non-standard key format: {key}"
                            )
                    except Exception as e:
                        logger.warning(f"Line {line_number}: Failed to parse key: {e}")
                        continue
                elif line:
                    logger.warning(
                        f"Line {line_number}: Malformed entry (no '='): {line}"
                    )

    except PermissionError:
        raise PermissionError(f"Unable to read {env_example_path} - permission denied")
    except UnicodeDecodeError:
        raise ValueError(f"File {env_example_path} contains invalid UTF-8 encoding")

    logger.info(
        f"Successfully parsed {len(keys)} environment variables from .env.example"
    )
    return keys


def get_settings_fields() -> Dict[str, str]:
    """
    Get all fields from Settings model with their validation_alias.

    Returns:
        Dict mapping field_name to validation_alias (or field_name if no alias)

    Raises:
        AttributeError: If Settings model doesn't have expected attributes
    """
    from pydantic import AliasChoices

    field_mappings = {}
    for field_name, field_info in Settings.model_fields.items():
        # Get validation_alias if it exists, otherwise use field_name
        alias = field_info.validation_alias or field_name.upper()

        # Handle AliasChoices objects (which are not hashable)
        if isinstance(alias, AliasChoices):
            # For AliasChoices, use the first choice as the representative alias
            alias = alias.choices[0] if alias.choices else field_name.upper()

        field_mappings[field_name] = alias

    return field_mappings


def _extract_field_alias(field_name: str, field_info: Any) -> str:
    """
    Safely extract validation alias from a Pydantic field.

    Args:
        field_name: Name of the field
        field_info: Pydantic field information object

    Returns:
        The validation alias or field name in uppercase
    """
    try:
        # Handle validation_alias attribute safely
        if hasattr(field_info, "validation_alias") and field_info.validation_alias:
            alias = field_info.validation_alias
            # Handle different alias types
            if isinstance(alias, str) and alias.strip():
                return alias.strip().upper()
            elif hasattr(alias, "first") and callable(alias.first):
                # Handle AliasPath or AliasChoices
                return field_name.upper()
            else:
                logger.warning(f"Unexpected alias type for {field_name}: {type(alias)}")
                return field_name.upper()
        else:
            # Fallback to field name in uppercase
            return field_name.upper()

    except Exception as e:
        logger.warning(f"Error extracting alias for {field_name}: {e}")
        return field_name.upper()


def get_exempted_keys() -> FrozenSet[str]:
    """
    Get list of keys that are exempted from the drift check.

    These are typically Bitwarden mapping IDs that don't directly map to Settings fields.

    Returns:
        Frozen set of exempted keys for immutability
    """
    exempted = {
        # Bitwarden Secret IDs (PRD environment)
        "BWS_ACCESS_TOKEN",
        "LINEAR_WEBHOOK_SECRET_PRD_ID",
        "POSTGRES_PASSWORD_PRD_ID",
        "NEO4J_PASSWORD_PRD_ID",
        "EXTENSION_API_KEY_PRD_ID",
        "LINEAR_API_KEY_PRD_ID",
        "PERPLEXITY_API_KEY_PRD_ID",
        "GEMINI_API_KEY_PRD_ID",
        "JWT_SECRET_KEY_ID",
        "OLLAMA_OKG_API_KEY_PRD_ID",
        # Legacy Bitwarden IDs (backward compatibility)
        "LINEAR_WEBHOOK_SECRET_ID",
        "POSTGRES_PASSWORD_ID",
        "NEO4J_PASSWORD_ID",
        "LINEAR_API_KEY_ID",
        "PERPLEXITY_API_KEY_ID",
        "GEMINI_API_KEY_ID",
        "NGROK_API_KEY_ID",
        "NANOGPT_DEV_API_KEY_ID",
        "EXTENSION_API_KEY_ID",
        # Docker infrastructure vars (used by docker-compose, not Settings)
        "POSTGRES_SERVER_DOCKER",
        "POSTGRES_PORT_DOCKER",
        "POSTGRES_SERVER_DOCKER_DEV",
        "POSTGRES_PORT_DOCKER_DEV",
        "NEO4J_URI_DOCKER",
        "NEO4J_URI_DOCKER_DEV",
        # Security configuration flags
        "ZERO_TRUST_REQUIRED",
        # Special format fields (don't require underscore)
        "VERSION",
        # Exemptions for optional / third-party configs not modeled in Settings
        "APIDOG_ACCESS_TOKEN",
        "APIDOG_PROJECT_ID",
        "OMEGA_ENV",
        "HOOKDECK_PUBLIC_URL",
    }

    return frozenset(exempted)


# Cache decorator for expensive operations
def memoize(func):
    """Simple memoization decorator for caching function results."""
    cache = {}

    def wrapper(*args, **kwargs):
        # Create a cache key from arguments
        key = str(args) + str(sorted(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


@memoize
def _get_cached_env_keys() -> FrozenSet[str]:
    """
    Parse .env.example and return cached set of environment variable keys.

    Returns:
        Frozen set of environment variable keys for immutability and caching
    """
    try:
        return frozenset(parse_env_example())
    except (FileNotFoundError, PermissionError, ValueError) as e:
        pytest.fail(f"Failed to parse .env.example: {e}")


@memoize
def _get_cached_settings_mappings() -> Dict[str, str]:
    """
    Get cached Settings field mappings to avoid repeated reflection.

    Returns:
        Immutable mapping of field names to their validation aliases
    """
    try:
        return get_settings_fields()
    except AttributeError as e:
        pytest.fail(f"Failed to extract Settings field mappings: {e}")


def _categorize_missing_entries(
    settings_mappings: Dict[str, str], env_keys: FrozenSet[str]
) -> Dict[str, List[Tuple[str, str]]]:
    """
    Categorize missing environment variables by type and severity.

    Args:
        settings_mappings: Field name to alias mappings from Settings
        env_keys: Available environment variable keys from .env.example

    Returns:
        Dictionary categorizing missing entries by type and severity
    """
    missing = {
        "critical": [],  # Required fields (Field(...))
        "optional": [],  # Optional fields with defaults
        "deprecated": [],  # Fields that might need cleanup
    }

    for field_name, alias in settings_mappings.items():
        if alias not in env_keys:
            # Categorize based on field characteristics
            try:
                field_info = Settings.model_fields.get(field_name)
                severity = _determine_field_severity(field_name, field_info)
                missing[severity].append((field_name, alias))
            except Exception as e:
                logger.warning(f"Error categorizing field {field_name}: {e}")
                missing["deprecated"].append((field_name, alias))

    return missing


def _determine_field_severity(field_name: str, field_info: Any) -> str:
    """
    Determine the severity level of a missing field.

    Args:
        field_name: Name of the field
        field_info: Pydantic field information

    Returns:
        Severity level: "critical", "optional", or "deprecated"
    """
    try:
        # Check if field is required
        if hasattr(field_info, "is_required") and field_info.is_required():
            return "critical"

        # Check if field has a default value
        if hasattr(field_info, "default") and field_info.default is not None:
            return "optional"

        # Check for ellipsis which indicates required field
        if hasattr(field_info, "default") and field_info.default is ...:
            return "critical"

        # Default to optional for uncertain cases
        return "optional"

    except Exception:
        # Fallback for any parsing errors
        return "deprecated"


def _fail_with_detailed_message(
    missing_entries: Dict[str, List[Tuple[str, str]]],
) -> None:
    """
    Generate detailed failure message with categorized missing entries.

    Args:
        missing_entries: Categorized list of missing environment variables
    """
    error_parts = []
    total_missing = sum(len(entries) for entries in missing_entries.values())

    error_parts.append(f"Configuration drift detected: {total_missing} missing entries")
    error_parts.append("")

    # Build detailed error message with categorization
    for category, entries in missing_entries.items():
        if entries:
            category_title = category.replace("_", " ").title()
            error_parts.append(f"{category_title} fields missing from .env.example:")

            for field_name, alias in sorted(entries):
                error_parts.append(f"  • {field_name} → expects {alias}")
            error_parts.append("")

    # Add actionable guidance
    error_parts.extend(
        [
            "Remediation steps:",
            "1. Review each missing entry above",
            "2. Add corresponding entries to .env.example",
            "3. Ensure proper documentation and default values",
            "4. Run tests again to verify resolution",
        ]
    )

    pytest.fail("\n".join(error_parts))


@pytest.mark.unit
def test_settings_have_env_example_entries():
    """
    Verify all Settings fields have corresponding .env.example entries.

    This test ensures configuration drift prevention by validating that every
    field in the Settings model has a corresponding environment variable
    definition in the .env.example file.
    """
    # Use cached results to avoid repeated file I/O in complex test scenarios
    env_keys = _get_cached_env_keys()
    settings_field_mappings = _get_cached_settings_mappings()

    # Identify missing environment variables with detailed categorization
    missing_entries = _categorize_missing_entries(settings_field_mappings, env_keys)

    if any(missing_entries.values()):
        _fail_with_detailed_message(missing_entries)


@pytest.mark.unit
def test_env_example_keys_exist_in_settings():
    """
    Verify all non-exempted .env.example keys exist in Settings.

    This test catches orphaned environment variables that don't map to any
    Settings field, which could indicate stale configuration.
    """
    try:
        env_keys = _get_cached_env_keys()
        settings_fields = _get_cached_settings_mappings()
        exempted = get_exempted_keys()

        # Get all valid aliases from Settings
        valid_aliases = set(settings_fields.values())

        # Find keys in .env.example that are not in Settings and not exempted
        orphaned_keys = []
        for key in env_keys:
            if key not in valid_aliases and key not in exempted:
                orphaned_keys.append(key)

        if orphaned_keys:
            pytest.fail(
                "Keys in .env.example not mapped to Settings fields:\n"
                + "\n".join(f"  - {key}" for key in sorted(orphaned_keys))
                + "\n\nEither add these to Settings or add to exemption list if they are Bitwarden mappings."
            )

    except Exception as e:
        pytest.fail(f"Error during orphaned keys validation: {e}")


@pytest.mark.unit
def test_bitwarden_id_keys_are_exempted():
    """
    Verify all *_ID keys in .env.example are properly exempted.

    This test ensures that all Bitwarden ID variables are properly handled
    and don't leak into the main Settings model.
    """
    try:
        env_keys = _get_cached_env_keys()
        exempted = get_exempted_keys()
        settings_fields = _get_cached_settings_mappings()
        valid_aliases = set(settings_fields.values())

        # Find ID keys that are not exempted and not in settings
        id_keys = {key for key in env_keys if key.endswith("_ID")}
        unexempted_ids = []

        for key in id_keys:
            if key not in exempted and key not in valid_aliases:
                unexempted_ids.append(key)

        if unexempted_ids:
            pytest.fail(
                "ID keys found that are not exempted:\n"
                + "\n".join(f"  - {key}" for key in sorted(unexempted_ids))
                + "\n\nAdd these to get_exempted_keys() in test_config_drift.py"
            )

    except Exception as e:
        pytest.fail(f"Error during Bitwarden ID validation: {e}")


@pytest.mark.unit
def test_env_example_exists():
    """
    Sanity check: Verify .env.example file exists.

    This test ensures the basic prerequisite for all other tests is met.
    """
    env_example_path = Path(__file__).parent.parent / ".env.example"
    assert env_example_path.exists(), f".env.example not found at {env_example_path}"


@pytest.mark.unit
def test_settings_can_be_instantiated():
    """
    Verify Settings can be instantiated (catches Pydantic validation errors).

    This test ensures the Settings model is properly configured and can be
    instantiated without runtime errors.
    """
    try:
        # This will use env vars or defaults
        settings = Settings()
        logger.info(f"Settings instantiated successfully: {settings.VERSION}")

        # Verify critical attributes exist
        assert hasattr(settings, "PROJECT_NAME"), "Settings missing PROJECT_NAME"
        assert hasattr(settings, "VERSION"), "Settings missing VERSION"
        assert hasattr(settings, "database_url"), (
            "Settings missing database_url property"
        )

    except Exception as e:
        pytest.fail(f"Failed to instantiate Settings: {e}")


def test_configuration_consistency():
    """
    Additional test to verify configuration consistency across different aspects.

    This test performs cross-validation of configuration settings to catch
    inconsistencies that might not be caught by the individual tests.
    """
    try:
        settings = Settings()
        _get_cached_env_keys()

        # Check that database URL components are consistent
        if hasattr(settings, "database_url"):
            assert settings.database_url.startswith("postgresql+asyncpg://"), (
                "database_url should use postgresql+asyncpg:// protocol"
            )

        # Check that port values are reasonable
        if hasattr(settings, "app_port"):
            assert 1 <= settings.app_port <= 65535, (
                f"Invalid app_port: {settings.app_port}"
            )

        if hasattr(settings, "postgres_port"):
            assert 1 <= settings.postgres_port <= 65535, (
                f"Invalid postgres_port: {settings.postgres_port}"
            )

        logger.info("Configuration consistency check passed")

    except Exception as e:
        pytest.fail(f"Configuration consistency check failed: {e}")
