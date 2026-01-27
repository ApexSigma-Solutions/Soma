"""
Mirmir - The Constraint Review Protocol

Mirmir reviews proposed actions against constraints and provides verdicts.
It implements the governance logic for the Intelligence Layer.
"""

import logging
from typing import List, Optional

from .codex import Codex
from .models import Constraint, Verdict, SeverityLevel
from .exceptions import CodexVetoError

logger = logging.getLogger(__name__)


class Mirmir:
    """
    The Constraint Review Protocol.

    Mirmir reviews proposed actions against constraints from the Codex
    and provides verdicts on whether the action should be approved.
    """

    def __init__(self, codex: Codex, omega4j: Optional[object] = None):
        """
        Initialize Mirmir with a Codex instance.

        Args:
            codex: Codex instance for retrieving constraints
            omega4j: Optional Omega4J instance for advanced constraint evaluation (not used in bootstrap mode)
        """
        self.codex = codex
        self.omega4j = omega4j
        logger.info("Mirmir initialized")

    def review_action(
        self,
        proposed_action: str,
        context_tags: List[str] = None,
        strict_mode: bool = False,
    ) -> Verdict:
        """
        Review a proposed action against constraints.

        Args:
            proposed_action: Description of the action to review
            context_tags: List of context tags to filter constraints
            strict_mode: If True, any violation results in veto

        Returns:
            Verdict object with approval status and details

        Raises:
            CodexVetoError: If action is vetoed (in strict mode)
        """
        logger.info(f"Reviewing action: '{proposed_action}'")
        logger.info(f"Context tags: {context_tags or ['all']}")

        # Retrieve relevant constraints
        constraints = self._get_relevant_constraints(context_tags)

        logger.info(f"Checking against {len(constraints)} constraints")

        # Evaluate constraints
        violations = []
        warnings = []

        for constraint in constraints:
            evaluation = self._evaluate_constraint(
                constraint, proposed_action, context_tags
            )

            if evaluation == "violate":
                violations.append(constraint.id)
                logger.warning(
                    f"⚠️  Violation: {constraint.id} - {constraint.description}"
                )
            elif evaluation == "warn":
                warnings.append(constraint.id)
                logger.info(f"⚠️  Warning: {constraint.id} - {constraint.description}")

        # Determine verdict
        approved = len(violations) == 0

        if not approved:
            message = f"Action vetoed due to {len(violations)} constraint violation(s)"
            if violations:
                message += f": {', '.join(violations)}"
        elif warnings:
            message = f"Action approved with {len(warnings)} warning(s)"
            if warnings:
                message += f": {', '.join(warnings)}"
        else:
            message = "Action approved - no constraints violated"

        verdict = Verdict(
            approved=approved,
            message=message,
            constraints_checked=[c.id for c in constraints],
            violations=violations,
            warnings=warnings,
        )

        logger.info(f"Verdict: {'APPROVED' if approved else 'VETOED'}")

        # Raise exception in strict mode if vetoed
        if strict_mode and not approved:
            raise CodexVetoError(verdict)

        return verdict

    def _get_relevant_constraints(
        self, context_tags: List[str] = None
    ) -> List[Constraint]:
        """
        Retrieve constraints relevant to the given context tags.

        Args:
            context_tags: List of context tags to filter constraints

        Returns:
            List of relevant Constraint objects
        """
        if not context_tags:
            # Get all constraints if no context specified
            return self.codex.get_constraints()

        # Get constraints for each context and merge
        constraints = []
        seen_ids = set()

        for context in context_tags:
            try:
                context_constraints = self.codex.get_constraints(context)
                for constraint in context_constraints:
                    if constraint.id not in seen_ids:
                        constraints.append(constraint)
                        seen_ids.add(constraint.id)
            except Exception as e:
                logger.warning(
                    f"Failed to get constraints for context '{context}': {e}"
                )

        return constraints

    def _evaluate_constraint(
        self,
        constraint: Constraint,
        proposed_action: str,
        context_tags: List[str] = None,
    ) -> str:
        """
        Evaluate a constraint against a proposed action.

        Args:
            constraint: Constraint to evaluate
            proposed_action: Action to evaluate
            context_tags: Context tags for the action

        Returns:
            "violate", "warn", or "pass"
        """
        # Bootstrap mode: Simple keyword matching
        # In production, this would use Omega4J for semantic analysis

        action_lower = proposed_action.lower()
        description_lower = constraint.description.lower()

        # Check for keyword matches
        keywords = self._extract_keywords(description_lower)

        for keyword in keywords:
            if keyword in action_lower:
                # Severity determines the outcome
                if constraint.severity == SeverityLevel.CRITICAL:
                    return "violate"
                elif constraint.severity == SeverityLevel.WARNING:
                    return "warn"
                else:
                    return "pass"

        return "pass"

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from constraint description.

        Args:
            text: Constraint description text

        Returns:
            List of keywords
        """
        # Simple keyword extraction
        # Remove common words and extract meaningful terms

        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "and",
            "but",
            "if",
            "or",
            "because",
            "as",
            "until",
            "while",
            "of",
            "at",
            "by",
            "for",
            "with",
            "about",
            "against",
            "between",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "to",
            "from",
            "up",
            "down",
            "in",
            "out",
            "on",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
        }

        # Split into words and filter
        words = text.split()
        keywords = []

        for word in words:
            # Remove punctuation
            word = word.strip(".,!?;:'\"()[]{}")
            # Check if it's a meaningful word (longer than 2 chars and not a stop word)
            if len(word) > 2 and word.lower() not in stop_words:
                keywords.append(word.lower())

        return keywords

    def check_constraint(self, constraint_id: str, proposed_action: str) -> bool:
        """
        Check if a specific constraint is violated by an action.

        Args:
            constraint_id: ID of the constraint to check
            proposed_action: Action to evaluate

        Returns:
            True if constraint is violated, False otherwise
        """
        try:
            constraint = self.codex.get_constraint(constraint_id)
            evaluation = self._evaluate_constraint(constraint, proposed_action)
            return evaluation == "violate"
        except Exception as e:
            logger.error(f"Failed to check constraint '{constraint_id}': {e}")
            return False
