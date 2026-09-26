"""Local configuration for Gmail notification searches."""

import tomllib
from pathlib import Path


def load_search_queries(path: Path) -> dict[str, str]:
    """Return named Gmail search queries from a local TOML file.

    Queries identify the operator's financial institutions, so they live in an
    ignored local file. Error messages name keys but never echo query values.
    """
    with Path(path).open("rb") as config_file:
        config = tomllib.load(config_file)

    searches = config.get("searches")
    if not isinstance(searches, dict) or not searches:
        raise ValueError("Search configuration needs a non-empty [searches] table.")

    for name, query in searches.items():
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Search {name!r} must be a non-empty string.")

    return dict(searches)
