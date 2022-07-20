from typing import Callable, Dict, List, Optional, Union

import requests
from she_logging import logger

from dhos_async_adapter.helpers import security
from dhos_async_adapter.helpers.exceptions import (
    RejectMessageError,
    RequeueMessageError,
)


def do_request(
    url: str,
    method: str,
    headers: Optional[Dict] = None,
    payload: Union[None, Dict, List] = None,
    params: Optional[Dict] = None,
    allow_http_error: bool = False,
    timeout: Optional[int] = 30,
) -> requests.Response:
    if headers is None:
        headers = security.get_request_headers()
    actual_method: Callable = getattr(requests, method)
    try:
        response: requests.Response = actual_method(
            url,
            params=params,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        logger.debug("Request completed with HTTP status code %d", response.status_code)
        if not allow_http_error:
            response.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 503:  # 503 Service Unavailable
            logger.exception("Error when connecting to API")
            raise RequeueMessageError()
        else:
            logger.exception("Unexpected response from API")
            raise RejectMessageError()
    except requests.RequestException:
        logger.exception("Error when connecting to API")
        raise RequeueMessageError()
    return response
