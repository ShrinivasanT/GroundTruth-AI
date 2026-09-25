class FactChatError(Exception):
    """Base application error."""


class DuplicatePaperError(FactChatError):
    """Raised when ingestion detects an already-indexed paper."""


class ExternalServiceError(FactChatError):
    """Raised when a dependent API returns an invalid response."""
