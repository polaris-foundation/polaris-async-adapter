import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jose
import requests
from jose import jwt as jose_jwt
from she_logging import logger
from she_logging.request_id import current_request_id

from dhos_async_adapter import config
from dhos_async_adapter.helpers.exceptions import RejectMessageError

SYSTEM_ID = "dhos-async-adapter"
HS_ISSUER: str = config.PROXY_URL
if not HS_ISSUER.endswith("/"):
    HS_ISSUER += "/"


def get_request_headers() -> Dict[str, str]:
    return {
        "X-Request-ID": current_request_id() or str(uuid.uuid4()),
        "Authorization": f"Bearer {_generate_system_jwt()}",
    }


def get_dea_request_headers() -> Dict[str, str]:
    return {
        "x-dhos-customer-code": config.CUSTOMER_CODE,
        "x-dhos-environment": config.ENVIRONMENT or "not-set",
        "X-Request-ID": current_request_id() or str(uuid.uuid4()),
        "authorization": f"Bearer {_retrieve_dea_auth0_jwt()}",
    }


def _generate_system_jwt() -> str:
    logger.info("Generating system JWT for system ID '%s'", SYSTEM_ID)
    claims = {
        "metadata": {"system_id": SYSTEM_ID},
        "iss": HS_ISSUER,
        "aud": HS_ISSUER,
        "scope": config.SYSTEM_JWT_SCOPE,
        "exp": datetime.utcnow() + timedelta(seconds=config.SYSTEM_JWT_EXPIRY_SEC),
    }
    jwt_token: str = jose_jwt.encode(
        claims=claims,
        key=config.HS_KEY,
        algorithm="HS512",
    )
    logger.debug(
        "Created system JWT for system ID '%s'", SYSTEM_ID, extra={"claims": claims}
    )
    return jwt_token


class DeaJwtCache:
    token: Optional[str] = None
    expiry: Optional[datetime] = None


dea_jwt_cache = DeaJwtCache()


def _retrieve_dea_auth0_jwt() -> str:
    """
    Retrieves a JWT from the DEA Auth0 tenant for talking to the central DEA services. Caches it to avoid
    hammering Auth0 with requests.
    """
    if (
        dea_jwt_cache.token is not None
        and dea_jwt_cache.expiry is not None
        and dea_jwt_cache.expiry - datetime.now(tz=timezone.utc) > timedelta(minutes=1)
    ):
        # Cached token has not expired and not going to expire in the next minute.
        return dea_jwt_cache.token
    logger.debug("No valid cached DEA Auth0 token, fetching a new one")
    payload = {
        "client_id": config.DEA_AUTH0_CLIENT_ID,
        "client_secret": config.DEA_AUTH0_CLIENT_SECRET,
        "audience": config.DEA_AUTH0_AUDIENCE,
        "grant_type": "client_credentials",
    }
    try:
        response = requests.post(
            url=config.DEA_AUTH0_TOKEN_URL,
            headers={"content-type": "application/x-www-form-urlencoded"},
            data=payload,
            timeout=30,
        )
        response.raise_for_status()
        access_token: str = response.json()["access_token"]
        dea_jwt_cache.token = access_token
        dea_jwt_cache.expiry = _get_expiry(access_token)
        return access_token
    except requests.exceptions.RequestException as e:
        logger.exception(
            "Couldn't retrieve JWT from DEA Auth0",
            extra={
                "response_status": getattr(e.response, "status_code", None),
                "response_data": getattr(e.response, "data", None),
            },
        )
        raise RejectMessageError()


def _get_expiry(token: str) -> datetime:
    """
    Returns the datetime at which the JWT is set to expire, or now + 15 minutes if none is provided.
    """
    try:
        exp: str = jose_jwt.get_unverified_claims(token)["exp"]
    except (jose.exceptions.JOSEError, KeyError):
        return datetime.now(tz=timezone.utc) + timedelta(minutes=15)
    return datetime.fromtimestamp(int(exp), tz=timezone.utc)
