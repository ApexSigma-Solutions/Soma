"""
Bootstrap script for InGest-LLM.as service.

Ensures all required NLP models and data are downloaded before starting the service.
"""

import sys
import subprocess


def download_spacy_model(model_name: str) -> bool:
    """Download a Spacy model if not already installed."""
    print(f"📦 Checking Spacy model: {model_name}")
    try:
        import spacy

        spacy.load(model_name)
        print(f"✅ Model {model_name} already installed")
        return True
    except OSError:
        print(f"⬇️  Downloading {model_name}...")
        result = subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"✅ Successfully downloaded {model_name}")
            return True
        else:
            print(f"❌ Failed to download {model_name}: {result.stderr}")
            return False


def download_nltk_data(package_name: str) -> bool:
    """Download NLTK data package if not already installed."""
    print(f"📦 Checking NLTK package: {package_name}")
    try:
        import nltk

        nltk.data.find(f"tokenizers/{package_name}")
        print(f"✅ Package {package_name} already installed")
        return True
    except LookupError:
        print(f"⬇️  Downloading {package_name}...")
        import nltk

        result = nltk.download(package_name, quiet=False)
        if result:
            print(f"✅ Successfully downloaded {package_name}")
            return True
        else:
            print(f"❌ Failed to download {package_name}")
            return False


def main():
    """Bootstrap InGest-LLM dependencies."""
    print("=" * 60)
    print("🚀 InGest-LLM.as Bootstrap")
    print("=" * 60)

    # Download Spacy model (try sm first for speed)
    spacy_models = ["en_core_web_sm", "en_core_web_md", "en_core_web_trf"]
    spacy_installed = False

    for model in spacy_models:
        if download_spacy_model(model):
            spacy_installed = True
            break

    if not spacy_installed:
        print("❌ Failed to install any Spacy model")
        return 1

    # Download NLTK data
    nltk_packages = ["punkt", "punkt_tab"]
    nltk_success = all(download_nltk_data(pkg) for pkg in nltk_packages)

    if not nltk_success:
        print("⚠️  Some NLTK packages failed to download")
        return 1

    print("\n" + "=" * 60)
    print("✅ All dependencies installed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
