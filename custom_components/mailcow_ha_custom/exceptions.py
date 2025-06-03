"""Exceptions spécifiques à l'intégration Mailcow."""

class MailcowAPIError(Exception):
    """Erreur générique liée à l'API Mailcow."""


class MailcowAuthenticationError(MailcowAPIError):
    """Erreur d'authentification avec l'API Mailcow."""


class MailcowConnectionError(MailcowAPIError):
    """Erreur de connexion à l'API Mailcow (réseau, timeout, etc.)."""
