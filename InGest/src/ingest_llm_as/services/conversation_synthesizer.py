import logging
import json
from typing import List, Dict, Any
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ingest_llm_as.config import get_settings

logger = logging.getLogger(__name__)


class ConversionDigest(BaseModel):
    title: str = Field(description="Suuggested title for the knowledge note")
    summary: str = Field(description="Concise summary of the conversation in markdown")
    entities: List[Dict[str, str]] = Field(
        description="Identified entities (name, type)"
    )
    relationships: List[Dict[str, str]] = Field(
        description="Relationships between entities (source, type, target)"
    )
    concepts: List[str] = Field(description="Key concepts discussed")
    decisions: List[str] = Field(description="Key decisions made")
    outcomes: List[str] = Field(description="Expected or achieved outcomes")
    tags: List[str] = Field(description="Relevant tags for categorization")


class ConversationSynthesizer:
    """
    Synthesizes raw conversation data into structured knowledge.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = self._init_client()

    def _init_client(self) -> AsyncOpenAI:
        if self.settings.llm_provider == "openai":
            return AsyncOpenAI(api_key=self.settings.openai_api_key)
        elif self.settings.llm_provider == "ollama":
            base_url = self.settings.ollama_base_url
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            return AsyncOpenAI(base_url=base_url, api_key="ollama")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")

    async def synthesize(
        self, messages: List[Dict[str, Any]], platform: str = "unknown"
    ) -> ConversionDigest:
        """
        Processes conversation messages and returns a structured digest.
        """
        if not messages:
            return ConversionDigest(
                title="Empty Conversation",
                summary="No content found.",
                entities=[],
                relationships=[],
                concepts=[],
                decisions=[],
                outcomes=[],
                tags=[],
            )

        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role.upper()}: {content}\n\n"

        system_prompt = (
            "You are a Knowledge Architect. Your task is to extract structured intelligence from an AI conversation.\n"
            "Analyze the conversation and return a JSON object with the following structure:\n"
            "- title: A short, descriptive title.\n"
            "- summary: A 2-3 paragraph markdown summary emphasizing technical value.\n"
            "- entities: List of {name, type} (e.g. {name: 'PostgreSQL', type: 'Database'}).\n"
            "- relationships: List of {source, type, target} (e.g. {source: 'InGest', type: 'WRITES_TO', target: 'PostgreSQL'}).\n"
            "- concepts: Abstract ideas (e.g. 'Vector Search', 'Saga Pattern').\n"
            "- decisions: Specific choices made during the chat.\n"
            "- outcomes: Resulting actions or status changes.\n"
            "- tags: Categories like #backend #architecture #fix.\n\n"
            "Return ONLY the JSON object. No preamble."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.summarization_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Platform: {platform}\n\nConversation:\n{conversation_text}",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            data = json.loads(response.choices[0].message.content)
            return ConversionDigest(**data)

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fallback
            return ConversionDigest(
                title=f"Failed Synthesis: {platform}",
                summary=f"Analysis failed due to error: {e}",
                entities=[],
                relationships=[],
                concepts=[],
                decisions=[],
                outcomes=[],
                tags=["#error"],
            )
