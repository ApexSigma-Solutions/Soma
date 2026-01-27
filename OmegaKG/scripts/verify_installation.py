#!/usr/bin/env python
"""
OmegaKG Installation Verification Script

Verifies that omega_kg package is properly installed in the current Python environment.
Provides detailed diagnostics and suggested fixes.
"""

import sys
import subprocess


def check_package_installed():
    """Check if omega_kg package can be imported."""
    try:
        import omega_kg

        print("[OK] omega_kg package is installed")
        try:
            version = getattr(omega_kg, "__version__", "unknown")
            print(f"[OK] Package version: {version}")
        except Exception:
            print("[OK] Package found but version not available")
        print(f"[OK] Package location: {omega_kg.__file__}")
        return True
    except ImportError as e:
        print(f"[ERROR] omega_kg package not found: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error importing omega_kg: {e}")
        return False


def check_virtual_environment():
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, "real_prefix") and (sys.real_prefix != sys.prefix)
    if in_venv:
        print(f"[OK] Running in virtual environment: {sys.prefix}")
    else:
        print("[WARNING] Not running in a virtual environment")
    return in_venv


def check_pip_list():
    """Check if omega_kg appears in pip list."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        packages = result.stdout
        if "omega_kg" in packages.lower():
            print("[OK] omega_kg found in pip list")
            return True
        else:
            print("[ERROR] omega_kg not found in pip list")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to run pip list: {e}")
        return False


def suggest_fix():
    """Provide suggested fix based on diagnostics."""
    print("\n" + "=" * 60)
    print("SUGGESTED FIX:")
    print("=" * 60)
    print("\nOption 1: Install in development mode (recommended)")
    print("  pip install -e .")
    print("\nOption 2: Install using Poetry")
    print("  poetry install")
    print("\nOption 3: Reinstall package")
    print("  pip uninstall omega_kg")
    print("  pip install -e .")
    print("\nOption 4: Verify virtual environment is activated")
    print("  Windows: .venv\\Scripts\\Activate.ps1")
    print("  Linux/Mac: source .venv/bin/activate")
    print("=" * 60 + "\n")


def main():
    """Main verification logic."""
    print("OmegaKG Installation Verification")
    print("=" * 60 + "\n")

    # Check virtual environment
    check_virtual_environment()
    print()

    # Check pip list
    pip_ok = check_pip_list()
    print()

    # Check package import
    import_ok = check_package_installed()
    print()

    # Provide fix suggestions if needed
    if not import_ok or not pip_ok:
        suggest_fix()
        sys.exit(1)
    else:
        print("[SUCCESS] All checks passed! omega_kg is properly installed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
