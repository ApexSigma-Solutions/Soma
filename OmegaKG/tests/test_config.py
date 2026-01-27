from pathlib import Path
from typing import Dict, List, Set

from omega_kg.settings import Settings  # Imports your Pydantic class


def get_settings_keys() -> Set[str]:
    """
    Returns the set of environment variable keys defined in the Settings class,
    using the validation_alias if defined, otherwise the field name.
    Supports Pydantic v2 including AliasChoices.

    Returns:
        Set[str]: Set of environment variable keys from Settings class
    """
    from pydantic import AliasChoices

    keys: Set[str] = set()
    for field_name, field_info in Settings.model_fields.items():
        # Get validation_alias if it exists, otherwise use field name
        if hasattr(field_info, "validation_alias") and field_info.validation_alias:
            alias = field_info.validation_alias
            # Handle AliasChoices: use first choice as canonical key
            if isinstance(alias, AliasChoices):
                keys.add(
                    str(alias.choices[0]).upper()
                    if alias.choices
                    else field_name.upper()
                )
            else:
                keys.add(str(alias).upper())
        else:
            keys.add(field_name.upper())
    return keys


def get_exempted_keys() -> Set[str]:
    """
    Get list of keys that are exempted from the drift check.
    These are typically Bitwarden mapping IDs that don't directly map to Settings fields.

    Returns:
        Set[str]: Set of exempted environment variable keys
    """
    return {
        # Bitwarden Secret IDs (not settings fields, used for secret injection)
        "BWS_ACCESS_TOKEN",
        "LINEAR_WEBHOOK_SECRET_PRD_ID",
        "POSTGRES_PASSWORD_PRD_ID",
        "NEO4J_PASSWORD_PRD_ID",
        "EXTENSION_API_KEY_PRD_ID",
        "LINEAR_API_KEY_PRD_ID",
        "PERPLEXITY_API_KEY_PRD_ID",
        "GEMINI_API_KEY_PRD_ID",
        "JWT_SECRET_KEY_ID",
        "NANOGPT_OMEGAKG_API_KEY",
        "OLLAMA_OKG_API_KEY_PRD_ID",
        # Legacy Bitwarden IDs (may still exist in some .env.example files)
        "LINEAR_WEBHOOK_SECRET_ID",
        "POSTGRES_PASSWORD_ID",
        "NEO4J_PASSWORD_ID",
        "LINEAR_API_KEY_ID",
        "PERPLEXITY_API_KEY_ID",
        "GEMINI_API_KEY_ID",
        "NGROK_API_KEY_ID",
        "NANOGPT_DEV_API_KEY_ID",
        "EXTENSION_API_KEY_ID",
        # Docker-internal routing (not used in Settings class)
        "POSTGRES_SERVER_DOCKER",
        "POSTGRES_PORT_DOCKER",
        "POSTGRES_SERVER_DOCKER_DEV",
        "POSTGRES_PORT_DOCKER_DEV",
        "NEO4J_URI_DOCKER",
        "NEO4J_URI_DOCKER_DEV",
        # Zero-trust enforcement (used by validation, not as field)
        "ZERO_TRUST_REQUIRED",
        # Legacy extension API key (handled via AliasChoices in Settings)
        "EXTENSION_API_KEY_PRD",
        "EXTENSION_API_KEY",
        # Optional parsing configs (not in Settings class)
        "LINEAR_USER_MAP_JSON",
        "LINEAR_LABEL_MAP_JSON",
        # External tools / optional envs not represented in Settings
        "APIDOG_ACCESS_TOKEN",
        "APIDOG_PROJECT_ID",
        # Environment marker used in CI / orchestration
        "OMEGA_ENV",
        # Hookdeck configuration
        "HOOKDECK_PUBLIC_URL",
    }


def parse_env_file(template_path: Path) -> Dict[str, str]:
    """
    Parse .env.example file and extract environment variable keys and values.

    Args:
        template_path (Path): Path to the .env.example file

    Returns:
        Dict[str, str]: Dictionary of environment variable keys and their values

    Raises:
        FileNotFoundError: If the template file doesn't exist
        Exception: If there are encoding issues reading the file
    """
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {template_path}")
    except Exception as e:
        raise Exception(f"Failed to read file: {template_path} - {e}")

    # Parse key-value pairs for better error reporting
    env_vars: Dict[str, str] = {}
    for line in template_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                env_vars[key] = value

    return env_vars


def test_config_drift() -> None:
    """
    Ensures .env.example and Pydantic Settings are in sync.
    Exempts Bitwarden ID keys and optional parsing configs.

    Raises:
        AssertionError: If config drift is detected between .env.example and Settings
    """
    template_path = Path(".env.example")

    # Parse environment file
    try:
        env_vars = parse_env_file(template_path)
        template_keys = set(env_vars.keys())
    except (FileNotFoundError, Exception) as e:
        raise AssertionError(f"Failed to read .env.example: {e}")

    # Get settings keys and exempted keys
    settings_keys = get_settings_keys()
    exempted_keys = get_exempted_keys()

    # Calculate differences
    missing_in_template = settings_keys - template_keys
    missing_in_settings = (template_keys - settings_keys) - exempted_keys

    # Build error messages
    error_messages: List[str] = []

    if missing_in_template:
        error_messages.append(
            f"Keys in Settings but NOT in .env.example: {sorted(missing_in_template)}"
        )

    if missing_in_settings:
        error_messages.append(
            f"Keys in .env.example but NOT in Settings (and not exempted): {sorted(missing_in_settings)}"
        )

    # Report results
    if error_messages:
        error_text = "\n".join(error_messages)
        hint = "Hint: Check both omega_kg/settings.py (Settings) and .env.example for mismatches."
        assert False, f"Config Drift Detected:\n{error_text}\n\n{hint}"

    # Success case - provide feedback
    print(
        f"✅ Config drift check passed! {len(settings_keys)} settings keys validated."
    )
    print(
        f"📋 Template contains {len(template_keys)} keys ({len(exempted_keys)} exempted)"
    )
