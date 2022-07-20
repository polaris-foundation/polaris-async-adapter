from typing import Dict, Type

import pytest

from dhos_async_adapter.helpers import actions
from dhos_async_adapter.helpers.exceptions import RejectMessageError


class TestActions:
    @pytest.mark.parametrize(
        "body,action_name,expected",
        [
            ({}, "some_action", RejectMessageError),
            ({"actions": []}, "some_action", RejectMessageError),
        ],
    )
    def test_extract_action_error(
        self, body: Dict, action_name: str, expected: Type[Exception]
    ) -> None:
        with pytest.raises(expected):
            actions.extract_action(body, action_name)
