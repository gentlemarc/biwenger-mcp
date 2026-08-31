"""Errores públicos seguros: nunca contienen cuerpos HTTP ni credenciales."""


class BiwengerError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def public(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}
