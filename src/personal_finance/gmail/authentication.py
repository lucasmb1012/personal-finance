"""OAuth authentication for Gmail."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def authenticate_gmail(
    credentials_path: Path,
    token_path: Path,
    scopes: Sequence[str] = (GMAIL_READONLY_SCOPE,),
) -> Any:
    """Return an authenticated Gmail client and persist a refreshed local token."""
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)
    credentials = _load_or_authorize_credentials(credentials_path, token_path, scopes)
    return build("gmail", "v1", credentials=credentials)


def _load_or_authorize_credentials(
    credentials_path: Path,
    token_path: Path,
    scopes: Sequence[str],
) -> Credentials:
    credentials = _load_token(token_path, scopes)

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
        credentials = flow.run_local_server(port=0)

    _save_token(token_path, credentials.to_json())
    return credentials


def _save_token(token_path: Path, token_json: str) -> None:
    """Write the token so that only the file owner can read or change it."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.touch(mode=0o600, exist_ok=True)
    token_path.chmod(0o600)
    token_path.write_text(token_json, encoding="utf-8")


def _load_token(token_path: Path, scopes: Sequence[str]) -> Credentials | None:
    if not token_path.exists():
        return None
    return Credentials.from_authorized_user_file(token_path, scopes)
