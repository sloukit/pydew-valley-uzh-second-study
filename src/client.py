import asyncio
from typing import Callable

from src import xplat
from src.settings import (
    # API_KEY,
    # PORT,
    # SERVER_IP,
    SERVER_URL,
    USE_SERVER,
)

# if USE_SERVER and sys.platform not in ("emscripten", "wasm"):
#     import requests  # type: ignore[import-untyped]


BAD_API_KEY = "9"

PLAY_TOKEN = "321"
BAD_PLAY_TOKEN_1 = "9"
BAD_PLAY_TOKEN_2 = "zzz"

DUMMY_TELEMETRY_DATA = {"self_assessment": "ok"}


def authn(
    play_token: str,
    post_login_callback: Callable[[dict], None],
    error_login_callback: Callable[[Exception], None],
) -> None:
    if USE_SERVER:
        url = f"{SERVER_URL}/authn"
        headers = {}
        payload = {
            "play_token": play_token,
        }
        # Do this all asynchronously:
        try:
            asyncio.create_task(
                xplat.post_request_with_callback(
                    url, headers, payload, post_login_callback, error_login_callback
                )
            )
        except Exception as err:
            error_login_callback(err)
    else:
        try:
            post_login_callback(
                {
                    "token": play_token,
                    "jwt": "dummy_token",
                    "game_version": 1,
                }
            )
        except Exception as err:
            error_login_callback(err)


def send_telemetry(encoded_jwt: str, payload: dict) -> None:
    """Send telemetry to the backend, asynchronously."""
    # TODO: If needed, we can restructure this to do async callbacks
    # as well, in case we need to react to this telemetry being sent.
    xplat.log(f"Sending telemetry: {payload}")
    url = f"{SERVER_URL}/telemetry"
    headers = {
        "Authorization": f"Bearer {encoded_jwt}",
    }
    asyncio.create_task(xplat.post_request(url, headers, payload))


async def _get_npc_status_internal(encoded_jwt: str, callback: Callable) -> dict | None:
    url = f"{SERVER_URL}/telemetry/npc_status/"
    headers = {
        "Authorization": f"Bearer {encoded_jwt}"
    }
    callback(await xplat.get_request(url, headers))


def get_npc_status(encoded_jwt: str, callback: Callable) -> None:
    xplat.log("Retrieving NPC status...")
    asyncio.create_task(_get_npc_status_internal(encoded_jwt, callback))

