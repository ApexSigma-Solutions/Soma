"""validate_env_example.py

Simple script to statically verify `.env.example` contains required env vars
declared in `omega_kg/settings.py` using Field(..., validation_alias=...).
This avoids importing `omega_kg.settings` (which would try to instanciate the settings
and fail without env vars).

Usage:
    python scripts/validate_env_example.py

Returns non-zero exit code if required env vars are missing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


SETTINGS_PATH = Path(__file__).parent.parent / "omega_kg" / "settings.py"
ENV_EXAMPLE_PATH = Path(__file__).parent.parent / ".env.example"


def parse_settings_for_env_vars(settings_file: Path) -> Dict[str, bool]:
    """
    Parse a simplified subset of `omega_kg/settings.py` to find Field(..., validation_alias=...) entries.

    Returns:
        dict mapping env_var_name -> is_required (True if Field(...) contains ellipsis '...')
    """
    text = settings_file.read_text(encoding="utf-8")

    # Pattern to find a variable assignment with a Field(...) call
    # Example: neo4j_password: str = Field(..., validation_alias="NEO4J_PASSWORD")
    field_pattern = re.compile(
        r"^\s*([A-Za-z0-9_]+)\s*:\s*[^=\n]+=\s*Field\((.*?)\)\s*#?.*$", re.M | re.S
    )

    # Pattern to find validation_alias inside Field(...)
    alias_pattern = re.compile(r"validation_alias\s*=\s*['\"]([A-Z0-9_]+)['\"]")

    required_map: Dict[str, bool] = {}
    for m in field_pattern.finditer(text):
        name, args = m.groups()
        alias_match = alias_pattern.search(args)
        if alias_match:
            env_name = alias_match.group(1)
        else:
            # Fallback: uppercase name
            env_name = name.upper()

        is_required = "..." in args
        required_map[env_name] = is_required

    return required_map


def parse_env_example(env_file: Path) -> Set[str]:
    """Read `.env.example` and return a set of keys (skip comments and blank lines)."""
    keys: Set[str] = set()
    if not env_file.exists():
        return keys

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            keys.add(key)
    return keys


def compare(
    settings_map: Dict[str, bool], env_keys: Set[str]
) -> Tuple[List[str], List[str]]:
    """Compare required env vars with `.env.example` keys.

    Returns a tuple (missing_required, extra_keys)
    - missing_required: required env vars that are not found in env_keys
    - extra_keys: env keys in `.env.example` that don't map to any Pydantic env var alias
    """
    required_envs = {k for k, v in settings_map.items() if v}
    all_envs_defined = set(settings_map.keys())

    missing_required = sorted(list(required_envs - env_keys))
    extra_keys = sorted(list(env_keys - all_envs_defined))

    return missing_required, extra_keys


def main() -> int:
    settings_map = parse_settings_for_env_vars(SETTINGS_PATH)
    env_keys = parse_env_example(ENV_EXAMPLE_PATH)

    missing_required, extra_keys = compare(settings_map, env_keys)

    if missing_required:
        print("Missing required env vars in .env.example:")
        for key in missing_required:
            print(f" - {key}")
    else:
        print("No required env vars missing in .env.example")

    if extra_keys:
        print("\nExtra keys in .env.example not referenced by settings.py (warning):")
        for key in extra_keys:
            print(f" - {key}")
    else:
        print("No extra keys found in .env.example")

    if missing_required:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
