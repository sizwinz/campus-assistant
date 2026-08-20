"""Application service exceptions."""


class ServiceError(Exception):
    """Error raised by application services with an HTTP-compatible status."""

    def __init__(self, status_code: int, detail: str, extra: dict | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.extra = extra or {}
