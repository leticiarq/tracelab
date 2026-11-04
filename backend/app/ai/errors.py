class AIError(Exception):
    status_code = 502

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AIDisabledError(AIError):
    status_code = 503


class AIUnavailableError(AIError):
    status_code = 503


class AIModelNotFoundError(AIError):
    status_code = 404


class AIIncompatibleModelError(AIError):
    status_code = 422


class AIInvalidResponseError(AIError):
    status_code = 502


class AITimeoutError(AIError):
    status_code = 504


class AIBusyError(AIError):
    status_code = 409


class AICancelledError(AIError):
    status_code = 499


class AIImageError(AIError):
    status_code = 422
