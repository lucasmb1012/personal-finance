"""Gmail adapters for local transaction ingestion."""

from personal_finance.gmail.authentication import authenticate_gmail
from personal_finance.gmail.configuration import load_search_queries
from personal_finance.gmail.search import list_message_ids

__all__ = [
    "authenticate_gmail",
    "list_message_ids",
    "load_search_queries",
]
