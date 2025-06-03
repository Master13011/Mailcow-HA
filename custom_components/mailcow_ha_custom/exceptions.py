"""Exceptions spécifiques à l'intégration Mailcow."""

class MailcowAPIError(Exception):
    """Erreur générique liée à l'API Mailcow."""
    def __init__(self, message=None):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message or self.__class__.__name__


class MailcowAuthenticationError(MailcowAPIError):
    """Erreur d'authentification avec l'API Mailcow."""


class MailcowConnectionError(MailcowAPIError):
    """Erreur de connexion à l'API Mailcow (réseau, timeout, etc.)."""
