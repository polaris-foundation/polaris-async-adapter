from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt as jose_jwt
from pytest_mock import MockFixture
from requests_mock import Mocker

from dhos_async_adapter import config
from dhos_async_adapter.config import DEFAULT_SYSTEM_JWT_SCOPE
from dhos_async_adapter.helpers import security
from dhos_async_adapter.helpers.exceptions import RejectMessageError


class TestAudit:
    @pytest.mark.freeze_time("2020-01-01T00:00:00.000+00:00")
    def test_get_request_headers(self, mocker: MockFixture) -> None:
        # Arrange
        request_id = "request_id"
        token = "TOKEN"
        mock_current_request_id = mocker.patch.object(
            security, "current_request_id", return_value=request_id
        )
        mock_jose_encode = mocker.patch.object(
            security.jose_jwt, "encode", return_value=token
        )

        # Act
        result = security.get_request_headers()

        # Assert
        expected_claims = {
            "metadata": {"system_id": "dhos-async-adapter"},
            "iss": "http://localhost/",
            "aud": "http://localhost/",
            "scope": DEFAULT_SYSTEM_JWT_SCOPE,
            "exp": datetime(2020, 1, 1, 0, 5, 0, 0),
        }
        assert mock_current_request_id.call_count == 1
        assert mock_jose_encode.call_count == 1
        mock_jose_encode.assert_called_with(
            claims=expected_claims, key=config.HS_KEY, algorithm="HS512"
        )
        assert result == {
            "Authorization": f"Bearer {token}",
            "X-Request-ID": request_id,
        }

    def test_retrieve_dea_auth0_jwt_failure(self, requests_mock: Mocker) -> None:
        # Arrange
        mock_jwt = requests_mock.post("http://dea-auth0-token", status_code=401)

        # Act
        with pytest.raises(RejectMessageError):
            security.get_dea_request_headers()

        # Assert
        assert mock_jwt.call_count == 1

    def test_retrieve_dea_auth0_jwt_caching(self, requests_mock: Mocker) -> None:
        """
        Tests that the token is cached, such that the request is only made once
        even if the function is called many times.
        """
        # Arrange
        access_token = jose_jwt.encode(
            claims={
                "iss": "http://localhost/",
                "aud": "http://localhost/",
                "exp": datetime.utcnow() + timedelta(seconds=300),
            },
            key="some_key",
            algorithm="HS512",
        )
        security.dea_jwt_cache = security.DeaJwtCache()
        mock_jwt = requests_mock.post(
            "http://dea-auth0-token", json={"access_token": access_token}
        )

        # Act
        for i in range(10):
            security.get_dea_request_headers()

        # Assert
        assert mock_jwt.call_count == 1

    @pytest.mark.parametrize(
        "expiry_seconds,expect_new_token",
        [
            (-300, True),
            (0, True),
            (55, True),
            (65, False),
            (300, False),
        ],
        ids=[
            "expired_5m_ago",
            "expired_now",
            "expires_in_55s",
            "expires_in_65s",
            "expires_in_5m",
        ],
    )
    def test_retrieve_dea_auth0_jwt_expired(
        self, requests_mock: Mocker, expiry_seconds: int, expect_new_token: bool
    ) -> None:
        """
        Tests that the cached token is expired or is going to expire in the next
        minute, a new one is requested.
        """
        # Arrange
        old_token_expiry: datetime = datetime.now(tz=timezone.utc) + timedelta(
            seconds=expiry_seconds
        )
        old_access_token = jose_jwt.encode(
            claims={
                "iss": "http://localhost/",
                "aud": "http://localhost/",
                "exp": old_token_expiry,
            },
            key="some_key",
            algorithm="HS512",
        )
        security.dea_jwt_cache.token = old_access_token
        security.dea_jwt_cache.expiry = old_token_expiry
        new_token_expiry: datetime = datetime.now(tz=timezone.utc) + timedelta(
            minutes=15
        )
        new_access_token = jose_jwt.encode(
            claims={
                "iss": "http://localhost/",
                "aud": "http://localhost/",
                "exp": new_token_expiry,
            },
            key="some_key",
            algorithm="HS512",
        )

        mock_jwt = requests_mock.post(
            "http://dea-auth0-token", json={"access_token": new_access_token}
        )

        # Act
        result = security.get_dea_request_headers()

        # Assert
        if expect_new_token:
            assert mock_jwt.call_count == 1
            assert result["authorization"] == f"Bearer {new_access_token}"
            assert security.dea_jwt_cache.token == new_access_token
            assert security.dea_jwt_cache.expiry - new_token_expiry < timedelta(
                seconds=1
            )
        else:
            assert mock_jwt.call_count == 0
            assert result["authorization"] == f"Bearer {old_access_token}"
            assert security.dea_jwt_cache.token == old_access_token
            assert security.dea_jwt_cache.expiry == old_token_expiry
