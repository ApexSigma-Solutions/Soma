import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI

from ingest_llm_as.config import get_settings

logger = logging.getLogger(__name__)


class LLMSummarizer:
    """
    Summarizes generic conversation data using the configured LLM provider.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = self._init_client()

    def _init_client(self) -> AsyncOpenAI:
        if self.settings.llm_provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API Key required when provider is 'openai'")
            return AsyncOpenAI(api_key=self.settings.openai_api_key)

        elif self.settings.llm_provider == "ollama":
            # Ollama provides an OpenAI-compatible endpoint
            base_url = self.settings.ollama_base_url
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            return AsyncOpenAI(
                base_url=base_url,
                api_key="ollama",  # Not used but required by client
            )

        elif self.settings.llm_provider == "nanogpt":
            if not self.settings.nanogpt_api_key:
                raise ValueError("NanoGPT API Key required when provider is 'nanogpt'")
            return AsyncOpenAI(
                base_url=self.settings.nanogpt_base_url,
                api_key=self.settings.nanogpt_api_key,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")

    async def summarize_conversation(
        self, messages: List[Dict[str, Any]], context: str = ""
    ) -> str:
        """
        Generate a concise summary of the provided conversation messages.
        """
        if not messages:
            return "No content to summarize."

        # Simplify messages for the prompt to save context winfow
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # Truncate very long messages
            if len(content) > 2000:
                content = content[:2000] + "...(truncated)"
            conversation_text += f"{role.upper()}: {content}\n\n"

        system_prompt = (
            "You are an expert technical writer and knowledge manager. "
            "Your goal is to summarize the following AI conversation into a concise, high-value note for a developer's knowledge base (Obsidian).\n"
            "Guidelines:\n"
            "- Focus on the Problem, the Solution, and Key Decisions.\n"
            "- Ignore chit-chat.\n"
            "- Use Markdown formatting (headers, bullet points).\n"
            "- If there are code snippets, describe what they do; do not copy them unless critical one-liners.\n"
            "- Start with a metadata block in YAML frontmatter format is NOT needed (logic handles that), just the content body.\n"
            "- Create a title suggestion as the first line starting with '# '."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.summarization_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context: {context}\n\nConversation:\n{conversation_text}",
                    },
                ],
                temperature=0.3,  # Low temperature for factual summary
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return f"Error generating summary: {e}"
