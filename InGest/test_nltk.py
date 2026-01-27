"""Test NLTK installation and punkt tokenizer."""

import nltk

try:
    # Try to use sent_tokenize
    test_text = "This is a test. This is another sentence."
    sentences = nltk.sent_tokenize(test_text)
    print(f"✅ NLTK punkt tokenizer working! Found {len(sentences)} sentences:")
    for i, sent in enumerate(sentences, 1):
        print(f"  {i}. {sent}")
except LookupError as e:
    print(f"❌ NLTK punkt tokenizer not found: {e}")
    print("Attempting to download...")
    nltk.download("punkt")
    nltk.download("punkt_tab")
    print("Download complete. Retrying...")
    sentences = nltk.sent_tokenize(test_text)
    print(f"✅ Now working! Found {len(sentences)} sentences")
