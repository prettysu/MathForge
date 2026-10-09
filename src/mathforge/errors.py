class MathForgeError(Exception):
    """Base exception for expected MathForge failures."""


class ValidationError(MathForgeError, ValueError):
    """Raised when a persisted object violates its data contract."""


class GateError(MathForgeError):
    """Raised when a run cannot pass a promotion gate."""

    def __init__(self, code: str, message: str, claim_id: str | None = None):
        self.code = code
        self.claim_id = claim_id
        self.message = message
        detail = f"{code}: {message}"
        if claim_id:
            detail = f"{detail} (claim {claim_id})"
        super().__init__(detail)
