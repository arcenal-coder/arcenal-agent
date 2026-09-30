"""Authentification des applications internes ARCenal."""

from __future__ import annotations

import hmac
import os
import re
from collections.abc import Callable

from .errors import ApplicationAuthenticationError
from .models import ApplicationIdentity


USER_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{1,128}$")
TokenResolver = Callable[[str], str]
MINIMUM_SECRET_LENGTH = 43


def is_strong_secret(value: str) -> bool:
    return len(value) >= MINIMUM_SECRET_LENGTH and len(set(value)) >= 16


def environment_token(application_id: str) -> str:
    key = "ARCENAL_APP_" + application_id.upper().replace("-", "_") + "_TOKEN"
    value = os.environ.get(key, "").strip()
    return value if is_strong_secret(value) else ""


class ApplicationAuthenticator:
    def __init__(self, token_resolver: TokenResolver = environment_token) -> None:
        self._token_resolver = token_resolver

    def authenticate(self, application_id: str, authorization: str | None, user_id: str | None) -> ApplicationIdentity:
        supplied = self._bearer_token(authorization)
        expected = self._token_resolver(application_id)
        if not is_strong_secret(expected) or not hmac.compare_digest(supplied, expected):
            raise ApplicationAuthenticationError("Preuve d’identité applicative invalide.")
        if user_id is not None and not USER_PATTERN.fullmatch(user_id):
            raise ApplicationAuthenticationError("Identité utilisateur invalide.")
        return ApplicationIdentity(application_id=application_id, user_id=user_id)

    def _bearer_token(self, authorization: str | None) -> str:
        if authorization is None:
            raise ApplicationAuthenticationError("Jeton applicatif Bearer requis.")
        scheme, separator, token = authorization.partition(" ")
        if separator != " " or scheme.lower() != "bearer" or not token.strip():
            raise ApplicationAuthenticationError("Jeton applicatif Bearer requis.")
        return token.strip()
