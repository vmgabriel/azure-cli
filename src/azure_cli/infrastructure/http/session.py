"""HTTP session factory for the Azure DevOps REST API."""

from __future__ import annotations

import requests
from requests.auth import HTTPBasicAuth

#: Azure DevOps authenticates with an empty user name and the PAT as password.
PAT_USER_NAME = ""


def build_session(
    pat: str,
    *,
    user_agent: str = "azure-cli",
) -> requests.Session:
    """Return a `requests.Session` pre-configured for Azure DevOps.

    The PAT travels in the ``Authorization`` header (HTTP basic auth) and is
    never written to the configuration files or the terminal.
    """
    session = requests.Session()
    session.auth = HTTPBasicAuth(PAT_USER_NAME, pat)
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
    )
    return session
