"""Fournisseur d’identité machine pour les applications ARCenal."""

from __future__ import annotations

import hmac
from typing import Optional

from hermes_cli.dashboard_auth import DashboardAuthProvider, LoginStart, Session, TokenPrincipal

from .auth import is_strong_secret


class ArcenalApplicationProvider(DashboardAuthProvider):
    name = "arcenal-applications"
    display_name = "Applications ARCenal"
    supports_token = True
    supports_session = False

    def __init__(self, tokens: dict[str, str]) -> None:
        self._tokens = {key: value for key, value in tokens.items() if is_strong_secret(value)}

    def verify_token(self, *, token: str) -> Optional[TokenPrincipal]:
        application = next((key for key, value in self._tokens.items() if hmac.compare_digest(token, value)), None)
        if application is None:
            return None
        return TokenPrincipal(principal=application, provider=self.name, scopes=("agents.query",))

    def start_login(self, *, redirect_uri: str) -> LoginStart:
        raise NotImplementedError

    def complete_login(self, *, code: str, state: str, code_verifier: str, redirect_uri: str) -> Session:
        raise NotImplementedError

    def verify_session(self, *, access_token: str) -> Optional[Session]:
        return None

    def refresh_session(self, *, refresh_token: str) -> Session:
        raise NotImplementedError

    def revoke_session(self, *, refresh_token: str) -> None:
        return None
