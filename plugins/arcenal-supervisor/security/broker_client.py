"""Client du broker root, accessible au seul service de contrôle ARCenal."""

from __future__ import annotations

import json
import os
import socket
from typing import Mapping


class BrokerUnavailableError(RuntimeError):
    """Signale une passerelle privilégiée absente ou invalide."""


def _socket_path(variable: str, fallback: str) -> str:
    return os.environ.get(variable, fallback)


def _receive(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while sum(map(len, chunks)) <= 1_048_576:
        chunk = connection.recv(65_536)
        if not chunk:
            break
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    return b"".join(chunks).split(b"\n", 1)[0]


def _execute_at(
    socket_path: str,
    payload: Mapping[str, object],
    timeout: float,
) -> dict[str, object]:
    """Transmet un contrat JSON fermé sans construire de commande shell."""
    message = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8") + b"\n"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout)
            connection.connect(socket_path)
            connection.sendall(message)
            raw = _receive(connection)
    except (OSError, TimeoutError) as exc:
        raise BrokerUnavailableError("La passerelle privilégiée ARCenal est indisponible.") from exc
    try:
        response = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BrokerUnavailableError("La passerelle a renvoyé une réponse invalide.") from exc
    if not isinstance(response, dict) or not isinstance(response.get("ok"), bool):
        raise BrokerUnavailableError("La passerelle a rompu son contrat de réponse.")
    return response


def execute(payload: Mapping[str, object], timeout: float = 125.0) -> dict[str, object]:
    """Utilise le canal réservé au service de contrôle authentifié."""
    socket_path = _socket_path(
        "ARCENAL_PRIVILEGED_SOCKET",
        "/run/arcenal-control/privileged.sock",
    )
    return _execute_at(socket_path, payload, timeout)


def execute_readonly(payload: Mapping[str, object], timeout: float = 65.0) -> dict[str, object]:
    """Utilise le canal de lecture que le moteur agentique peut interroger."""
    socket_path = _socket_path(
        "ARCENAL_READONLY_SOCKET",
        "/run/arcenal-readonly/query.sock",
    )
    return _execute_at(socket_path, payload, timeout)
