from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def parse_html_content(html_content: str, url: str) -> list:
    """Factory: Selects parser based on URL."""
    soup = BeautifulSoup(html_content, "html.parser")
    if "aistudio.google.com" in url:
        return _parse_ai_studio(soup)
    elif "nano-gpt.com" in url:
        return _parse_nano_gpt(soup)
    return _parse_generic_fallback(soup)


def _parse_ai_studio(soup: BeautifulSoup) -> list:
    messages = []
    # Heuristic: Look for semantic containers or labeled text
    # This generic approach works for standard Google MD rendering
    chunks = soup.find_all(["div", "section"], class_=lambda x: x and "message" in x)
    if not chunks:
        return _parse_generic_fallback(soup)

    for chunk in chunks:
        text = chunk.get_text(separator="\n", strip=True)
        if text:
            role = "user" if "Run" in text or "User" in text else "assistant"
            messages.append({"role": role, "content": text})
    return messages


def _parse_nano_gpt(soup: BeautifulSoup) -> list:
    messages = []
    # Nano-GPT often uses Tailwind 'whitespace-pre-wrap' for chat bubbles
    bubbles = soup.select("div.whitespace-pre-wrap")
    if not bubbles:
        return _parse_generic_fallback(soup)

    for i, bubble in enumerate(bubbles):
        text = bubble.get_text(separator="\n", strip=True)
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": text})
    return messages


def _parse_generic_fallback(soup: BeautifulSoup) -> list:
    paras = soup.find_all("p")
    full_text = "\n\n".join([p.get_text() for p in paras])
    return [
        {"role": "system", "content": "Parsed via generic fallback"},
        {"role": "assistant", "content": full_text[:3000]},
    ]
