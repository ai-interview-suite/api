class AIServiceError(Exception):
    """Base exception for AI service errors."""


class AIServiceUnavailableError(AIServiceError):
    """Raised when the AI provider is unavailable."""


class AIResponseValidationError(AIServiceError):
    """Raised when the AI response is invalid."""