class InvalidCardError(Exception):
    pass


class InvalidMatchIdError(Exception):
    pass


class InvalidSetError(Exception):
    pass


class TargetSecretError(Exception):
    pass


class SetUpdateError(Exception):
    """Lanzado cuando la actualización del Set falla."""
    pass
