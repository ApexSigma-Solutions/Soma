"""
Document Parser Module for CortexBridge InGest-LLMs Engine.

This module provides extractive NLP parsing capabilities using Spacy Transformers
and NLTK for sentence tokenization. It converts long-form text into structured
Knowledge Graphs (Nodes & Edges) with data provenance.
"""

from __future__ import annotations

import logging
import os
import json
from enum import Enum
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from ingest_llm_as.config import get_settings

import spacy
from spacy.tokens import Doc
from spacy.language import Language

logger = logging.getLogger(__name__)


class ExtractionMode(str, Enum):
    """Configurable entity extraction modes.

    NER_ONLY: Extract only Named Entities (PERSON, ORG, GPE, etc.) - Default, most accurate
    SVO: Extract all Subject-Verb-Object triples (original behavior) - Most inclusive
    HYBRID: Extract NER entities with relationship inference between them - Balanced
    LLM_INFERENCE: Use an LLM to extract complex entities and relationships - Most intelligent
    """

    NER_ONLY = "ner_only"
    SVO = "svo"
    HYBRID = "hybrid"
    LLM_INFERENCE = "llm_inference"


class DocumentParser:
    """
    Extractive NLP parser for converting text to Knowledge Graphs.

    Uses Spacy Transformers (en_core_web_trf) for high-fidelity
    Entity & Relationship extraction, and NLTK for sentence tokenization.

    Attributes:
        nlp: Spacy language model loaded at initialization
        model_name: Name of the loaded Spacy model
    """

    # Model priority list (in order of preference)
    MODEL_PRIORITY = [
        "en_core_web_trf",  # Transformer-based (best accuracy, largest)
        "en_core_web_md",  # Transformer-based (good accuracy, medium)
        "en_core_web_sm",  # CNN-based (fastest, smallest)
    ]

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize DocumentParser with a Spacy Transformer model.

        Args:
            model_name: Name of Spacy model to load. If None, will try
                      models in priority order, falling back to lighter models.
                      Can also be set via SPACY_MODEL environment variable.

        Raises:
            ImportError: If Spacy is not installed or no model can be loaded
        """
        # Get model from environment variable or parameter
        if model_name is None:
            model_name = os.getenv("SPACY_MODEL", "")

        self.model_name = model_name
        self.nlp: Language | None = None

        # Try to load the specified model or fallback through priority list
        models_to_try = [model_name] if model_name else []
        models_to_try.extend([m for m in self.MODEL_PRIORITY if m not in models_to_try])

        for attempt_model in models_to_try:
            try:
                self.nlp = spacy.load(attempt_model)
                logger.info("Loaded Spacy model: %s", attempt_model)
                return  # Success - exit early
            except OSError as e:
                logger.warning("Failed to load Spacy model '%s': %s", attempt_model, e)
                if attempt_model != models_to_try[-1]:
                    logger.info("Trying next model in priority list...")
                    continue
                else:
                    # Last attempt failed - provide helpful error
                    logger.error("All Spacy models failed to load.")
                    logger.error(
                        "Please install a model using one of:\n"
                        "  python -m spacy download en_core_web_trf  (best accuracy)\n"
                        "  python -m spacy download en_core_web_md   (good accuracy)\n"
                        "  python -m spacy download en_core_web_sm   (fastest)"
                    )
                    logger.error(
                        "Or set SPACY_MODEL environment variable to your preferred model."
                    )
                    raise ImportError(
                        f"No Spacy model could be loaded. Tried: {', '.join(models_to_try)}. "
                        "Install with: python -m spacy download <model_name>"
                    ) from e
            except Exception as e:
                logger.error("Unexpected error loading Spacy model: %s", e)
                raise

    def preprocess(self, text: str) -> List[str]:
        """
        Preprocess text by cleaning and splitting into sentences.

        Uses NLTK's sent_tokenize for superior sentence splitting compared
        to Spacy's default sentence splitter.

        Args:
            text: Raw input text to preprocess

        Returns:
            List of cleaned sentences

        Raises:
            ImportError: If NLTK is not installed
        """
        try:
            import nltk
        except ImportError as e:
            logger.error("NLTK not installed: %s", e)
            logger.error("Please install NLTK: pip install nltk")
            logger.error("Download NLTK data: python -m nltk.downloader punkt")
            raise ImportError(
                "NLTK not installed. Install with: pip install nltk"
            ) from e

        # Clean whitespace
        cleaned_text = " ".join(text.split())

        # Use NLTK for sentence tokenization (superior to Spacy's default)
        try:
            sentences: List[str] = nltk.sent_tokenize(cleaned_text)
        except LookupError as e:
            logger.error("NLTK punkt tokenizer not found: %s", e)
            logger.error("Download NLTK data: python -m nltk.downloader punkt")
            raise ImportError(
                "NLTK punkt tokenizer not found. "
                "Download with: python -m nltk.downloader punkt"
            ) from e

        logger.debug("Preprocessed text into %s sentences", len(sentences))
        return sentences

    def _expand_compound_noun(self, token: Any) -> str:
        """
        Expand compound nouns to capture full entity phrases.

        For example, "ApexSigma Design System" should be captured as a single
        entity rather than just "ApexSigma" or "Design System".

        Args:
            token: Spacy token to expand

        Returns:
            Full compound noun phrase
        """
        # Collect all tokens that are part of the compound noun phrase
        compound_tokens = [token]
        to_process = list(token.children)

        while to_process:
            child = to_process.pop(0)
            if child.dep_ == "compound":
                compound_tokens.append(child)
                # Recursively check children of compound words
                to_process.extend(child.children)

        # Sort by position in text to maintain correct order
        compound_tokens.sort(key=lambda t: t.i)

        return " ".join([t.text for t in compound_tokens])

    def extract_relations(
        self, doc: Doc, context_text: str | None = None
    ) -> Dict[str, Any]:
        """
        Extract entities and relationships from Spacy document using dependency parsing.

        Iterates through tokens to identify VERB tokens and their children
        (nsubj, dobj, pobj) to extract subject-verb-object triples.

        Args:
            doc: Spacy processed document
            context_text: The original sentence text to use as a description

        Returns:
            Dictionary with 'nodes' and 'edges' keys representing the Knowledge Graph
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        seen_entities: set[str] = set()

        # Use the document text as context if not provided
        description = context_text or doc.text

        for token in doc:
            # Focus on VERB tokens as relationship anchors
            if token.pos_ != "VERB":
                continue

            # Extract subject (nominal subject)
            subject = None
            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    subject_text = self._expand_compound_noun(child)
                    subject = {
                        "id": subject_text,
                        "pos": child.pos_,
                        "label": self._classify_entity_type(child),
                        "description": description,
                    }
                    break

            # Extract object (direct object)
            obj = None
            for child in token.children:
                if child.dep_ == "dobj":
                    obj_text = self._expand_compound_noun(child)
                    obj = {
                        "id": obj_text,
                        "pos": child.pos_,
                        "label": self._classify_entity_type(child),
                        "description": description,
                    }
                    break

            # Extract prepositional object (object of preposition)
            pobj = None
            for child in token.children:
                if child.dep_ == "pobj":
                    pobj_text = self._expand_compound_noun(child)
                    pobj = {
                        "id": pobj_text,
                        "pos": child.pos_,
                        "label": self._classify_entity_type(child),
                        "description": description,
                    }
                    break

            # Only create edge if we have at least subject and one object
            if subject and (obj or pobj):
                # Add subject node if not seen
                if subject["id"] not in seen_entities:
                    nodes.append(subject)
                    seen_entities.add(subject["id"])

                # Add object node if not seen
                if obj and obj["id"] not in seen_entities:
                    nodes.append(obj)
                    seen_entities.add(obj["id"])

                if pobj and pobj["id"] not in seen_entities:
                    nodes.append(pobj)
                    seen_entities.add(pobj["id"])

                # Create edge: subject --[verb]--> object
                edge = {
                    "source": subject["id"],
                    "target": (obj or pobj)["id"],
                    "relationship": token.lemma_,
                    "source_pos": subject["pos"],
                    "target_pos": (obj or pobj)["pos"],
                }
                edges.append(edge)

        logger.debug("Extracted %s nodes and %s edges", len(nodes), len(edges))
        return {"nodes": nodes, "edges": edges}

    def extract_named_entities(
        self, doc: Doc, context_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract ONLY named entities (NER) from document.

        This method filters for meaningful entities recognized by Spacy's NER:
        PERSON, ORG, GPE, PRODUCT, WORK_OF_ART, etc.

        Args:
            doc: Spacy processed document
            context_text: The original sentence text for description

        Returns:
            Dictionary with 'nodes' and 'edges' keys
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        seen_entities: set[str] = set()

        description = context_text or doc.text

        # Extract all named entities from doc.ents
        entity_list = []
        for ent in doc.ents:
            if ent.text not in seen_entities:
                node = {
                    "id": ent.text,
                    "pos": "PROPN",  # Named entities are proper nouns
                    "label": ent.label_,
                    "description": description,
                }
                nodes.append(node)
                seen_entities.add(ent.text)
                entity_list.append(ent)

        # Create relationships between co-occurring entities in same sentence
        for i, ent1 in enumerate(entity_list):
            for ent2 in entity_list[i + 1 :]:
                # Find relationship verb between entities
                rel_verb = self._find_connecting_verb(doc, ent1, ent2)
                if rel_verb:
                    edges.append(
                        {
                            "source": ent1.text,
                            "target": ent2.text,
                            "relationship": rel_verb,
                            "source_pos": "PROPN",
                            "target_pos": "PROPN",
                        }
                    )

        logger.debug(
            "NER extracted %s entities and %s relationships", len(nodes), len(edges)
        )
        return {"nodes": nodes, "edges": edges}

    def _find_connecting_verb(self, doc: Doc, ent1: Any, ent2: Any) -> Optional[str]:
        """
        Find a verb connecting two entities in the dependency tree.

        Args:
            doc: Spacy document
            ent1: First entity
            ent2: Second entity

        Returns:
            Verb lemma if found, else 'relates_to'
        """
        # Find verbs between the two entities
        start_idx = min(ent1.start, ent2.start)
        end_idx = max(ent1.end, ent2.end)

        for token in doc[start_idx:end_idx]:
            if token.pos_ == "VERB":
                return token.lemma_

        # Default relationship if no verb found
        return "relates_to"

    def _classify_entity_type(self, token: Any) -> str:
        """
        Classify entity type based on Spacy NER and POS tags.

        Args:
            token: Spacy token to classify

        Returns:
            Entity type string (PERSON, ORG, PRODUCT, GPE, etc.)
        """
        # Check for named entity recognition
        if token.ent_type_:
            return token.ent_type_

        # Fallback to POS-based classification
        pos_mapping = {
            "PROPN": "PERSON",  # Proper noun
            "ORG": "ORG",  # Organization
            "GPE": "GPE",  # Geopolitical entity
            "LOC": "GPE",  # Location
            "PRODUCT": "PRODUCT",  # Product
            "EVENT": "EVENT",  # Event
            "WORK_OF_ART": "WORK_OF_ART",  # Work of art
            "LAW": "LAW",  # Law
            "LANGUAGE": "LANGUAGE",  # Language
            "DATE": "DATE",  # Date
            "TIME": "TIME",  # Time
            "PERCENT": "PERCENT",  # Percent
            "MONEY": "MONEY",  # Money
            "QUANTITY": "QUANTITY",  # Quantity
            "ORDINAL": "ORDINAL",  # Ordinal
            "CARDINAL": "CARDINAL",  # Cardinal
        }

        return pos_mapping.get(token.pos_, "ENTITY")

    async def extract_with_llm(self, text: str) -> Dict[str, Any]:
        """
        Use an LLM to extract entities and relationships from text.
        Returns nodes and edges in graph format.
        """
        settings = get_settings()

        # Initialize client
        if settings.llm_provider == "openai":
            if not settings.openai_api_key:
                logger.error("OpenAI API Key missing")
                return {"nodes": [], "edges": []}
            client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif settings.llm_provider == "ollama":
            base_url = settings.ollama_base_url
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            client = AsyncOpenAI(base_url=base_url, api_key="ollama")
        else:
            return {"nodes": [], "edges": []}

        system_prompt = (
            "You are an expert knowledge engineer. Extract entities and relationships from the following text into a Knowledge Graph JSON format.\n"
            "Output ONLY a raw JSON object with this exact structure:\n"
            "{\n"
            '  "nodes": [{"id": "UniqueId", "label": "PERSON|ORG|TECH|CONCEPT", "pos": "NOUN", "description": "context"}],\n'
            '  "edges": [{"source": "Id1", "target": "Id2", "relationship": "relationship_verb"}]\n'
            "}\n"
            "Be precise and extractive. Do not invent facts. Avoid very generic nodes."
        )

        try:
            logger.info("Requesting LLM relationship extraction...")
            response = await client.chat.completions.create(
                model=settings.summarization_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            content = response.choices[0].message.content
            if not content:
                return {"nodes": [], "edges": []}

            data = json.loads(content)
            return {"nodes": data.get("nodes", []), "edges": data.get("edges", [])}
        except Exception as e:
            logger.error(f"LLM Extraction failed: {e}")
            return {"nodes": [], "edges": []}

    async def parse(
        self, text: str, extraction_mode: ExtractionMode = ExtractionMode.NER_ONLY
    ) -> Dict[str, Any]:
        """
        Parse text into a Knowledge Graph structure.

        Orchestrates the full pipeline:
        1. Preprocess text (clean, sentence tokenize)
        2. Process each sentence with Spacy
        3. Extract entities and relationships (extractive or LLM based)
        4. Return structured graph
        """
        if self.nlp is None:
            raise RuntimeError("DocumentParser not initialized. Model not loaded.")

        logger.info(
            "Parsing text (%s characters) in %s mode", len(text), extraction_mode
        )

        # Handle LLM mode separately as it can process larger chunks or full text
        if extraction_mode == ExtractionMode.LLM_INFERENCE:
            llm_result = await self.extract_with_llm(text)
            from datetime import datetime

            return {
                "metadata": {
                    "parser": "llm_inference",
                    "model": "llm",
                    "mode": extraction_mode.value,
                    "timestamp": datetime.now().isoformat(),
                },
                "nodes": llm_result["nodes"],
                "edges": llm_result["edges"],
            }

        # Step 1: Preprocess text for extractive modes
        sentences = self.preprocess(text)

        all_nodes: List[Dict[str, Any]] = []
        all_edges: List[Dict[str, Any]] = []
        seen_entities: set[str] = set()

        for i, sentence in enumerate(sentences):
            try:
                doc = self.nlp(sentence)

                # Extract entities and relations based on mode
                if extraction_mode == ExtractionMode.NER_ONLY:
                    result = self.extract_named_entities(doc, context_text=sentence)
                elif extraction_mode == ExtractionMode.SVO:
                    result = self.extract_relations(doc, context_text=sentence)
                else:  # HYBRID
                    ner_result = self.extract_named_entities(doc, context_text=sentence)
                    svo_result = self.extract_relations(doc, context_text=sentence)
                    result = {
                        "nodes": ner_result["nodes"],
                        "edges": svo_result["edges"] + ner_result["edges"],
                    }

                # Merge nodes, avoiding duplicates
                for node in result["nodes"]:
                    if node["id"] not in seen_entities:
                        all_nodes.append(node)
                        seen_entities.add(node["id"])

                # Add all edges (redundancy handled by Neo4j later)
                all_edges.extend(result["edges"])

            except Exception as e:
                logger.error(f"Error parsing sentence {i}: {e}")
                continue

        # Remove duplicate edges
        unique_edges = []
        seen_edges = set()
        for edge in all_edges:
            edge_key = (
                edge["source"],
                edge.get("type") or edge.get("relationship"),
                edge["target"],
            )
            if edge_key not in seen_edges:
                unique_edges.append(edge)
                seen_edges.add(edge_key)

        from datetime import datetime

        return {
            "metadata": {
                "parser": "document_parser",
                "model": self.model_name,
                "mode": extraction_mode.value,
                "timestamp": datetime.now().isoformat(),
            },
            "nodes": all_nodes,
            "edges": unique_edges,
        }
