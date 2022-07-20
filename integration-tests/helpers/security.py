import uuid
from datetime import datetime, timedelta

from behave.runner import Context
from environs import Env
from jose import jwt as jose_jwt


def generate_system_jwt() -> str:
    return jose_jwt.encode(
        claims={
            "metadata": {"system_id": "integration-tests"},
            "iss": "http://localhost/",
            "aud": "http://localhost/",
            "scope": Env().str("SYSTEM_JWT_SCOPE"),
            "exp": datetime.utcnow() + timedelta(seconds=300),
        },
        key=Env().str("HS_KEY"),
        algorithm="HS512",
    )


def generate_device_jwt(context: Context) -> str:

    if not hasattr(context, "device_id"):
        context.device_id = str(uuid.uuid4())

    return jose_jwt.encode(
        claims={
            "iss": "http://localhost/",
            "aud": "http://localhost/",
            "scope": Env().str("MOCK_DEVICE_SCOPE"),
            "metadata": {"device_id": context.device_id},
            "exp": datetime.utcnow() + timedelta(seconds=300),
        },
        key=Env().str("HS_KEY"),
        algorithm="HS512",
    )
