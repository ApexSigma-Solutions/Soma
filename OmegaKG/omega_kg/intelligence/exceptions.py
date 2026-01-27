"""
Custom exceptions for the Intelligence Layer
"""


class IntelligenceError(Exception):
    """Base exception for Intelligence Layer errors"""

    pass


class CodexVetoError(IntelligenceError):
    """
    Raised when an action is vetoed by Mirmir.

    This exception should be caught by agents to handle constraint violations.
    """

    def __init__(self, verdict: "Verdict", message: str = None):
        self.verdict = verdict
        self.message = message or verdict.message
        super().__init__(self.message)


class CodexConnectionError(IntelligenceError):
    """Raised when Codex cannot connect to Neo4j"""

    pass


class ConstraintNotFoundError(IntelligenceError):
    """Raised when a constraint cannot be found"""

    pass


class ContextNotFoundError(IntelligenceError):
    """Raised when a context cannot be found"""

    pass
