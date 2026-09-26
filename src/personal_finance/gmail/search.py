"""Gmail message searches used by transaction ingestion."""

from typing import Any


def list_message_ids(service: Any, query: str) -> list[str]:
    """Return every Gmail message ID matching ``query`` without fetching bodies."""
    message_ids: list[str] = []
    page_token: str | None = None

    while True:
        request = service.users().messages().list(
            userId="me",
            q=query,
            pageToken=page_token,
        )
        response = request.execute()
        message_ids.extend(message["id"] for message in response.get("messages", []))
        page_token = response.get("nextPageToken")
        if page_token is None:
            return message_ids
