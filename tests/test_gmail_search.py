"""Tests for Gmail search adapters."""

import unittest

from personal_finance.gmail.search import list_message_ids


class FakeRequest:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response

    def execute(self) -> dict[str, object]:
        return self._response


class FakeMessages:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def list(self, **kwargs: object) -> FakeRequest:
        self.calls.append(kwargs)
        return FakeRequest(self._responses.pop(0))


class FakeUsers:
    def __init__(self, messages: FakeMessages) -> None:
        self._messages = messages

    def messages(self) -> FakeMessages:
        return self._messages


class FakeService:
    def __init__(self, messages: FakeMessages) -> None:
        self._users = FakeUsers(messages)

    def users(self) -> FakeUsers:
        return self._users


class TestGmailSearch(unittest.TestCase):
    def test_list_message_ids_collects_every_page(self) -> None:
        messages = FakeMessages(
            [
                {"messages": [{"id": "first"}], "nextPageToken": "next"},
                {"messages": [{"id": "second"}]},
            ]
        )

        message_ids = list_message_ids(FakeService(messages), "from:example.test")

        self.assertEqual(["first", "second"], message_ids)
        self.assertEqual("from:example.test", messages.calls[0]["q"])
        self.assertIsNone(messages.calls[0]["pageToken"])
        self.assertEqual("next", messages.calls[1]["pageToken"])

    def test_list_message_ids_returns_empty_list_without_matches(self) -> None:
        messages = FakeMessages([{}])

        message_ids = list_message_ids(FakeService(messages), "from:example.test")

        self.assertEqual([], message_ids)
