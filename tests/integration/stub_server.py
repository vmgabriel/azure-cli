"""A stub Azure DevOps server used by the integration tests.

It speaks just enough of the REST API to exercise the real HTTP stack
(`requests` included) without touching the network.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import urlparse

WORK_ITEM_42: dict[str, Any] = {
    "id": 42,
    "url": "https://dev.azure.com/acme/widgets/_apis/wit/workItems/42",
    "fields": {
        "System.Id": 42,
        "System.Title": "Login fails on Safari",
        "System.State": "Active",
        "System.WorkItemType": "Bug",
        "System.Description": "<div>The form does <b>not</b> submit.</div>",
        "Microsoft.VSTS.Common.AcceptanceCriteria": "<ul><li>The user can log in</li></ul>",
        "System.Tags": "frontend; p1",
        "Microsoft.VSTS.Scheduling.StoryPoints": 3,
        "System.AreaPath": "Acme/Frontend",
        "System.IterationPath": "Acme/Sprint 12",
        "System.AssignedTo": {"displayName": "Ada Lovelace", "uniqueName": "ada@acme.com"},
        "System.CreatedBy": {"displayName": "Alan Turing"},
    },
    "relations": [
        {
            "rel": "ArtifactLink",
            "url": "https://dev.azure.com/acme/widgets/_apis/git/repositories/repo1/pullRequests/7",
            "attributes": {"name": "Pull Request", "id": "7"},
        }
    ],
}

WORK_ITEM_43: dict[str, Any] = {
    "id": 43,
    "url": "https://dev.azure.com/acme/widgets/_apis/wit/workItems/43",
    "fields": {
        "System.Id": 43,
        "System.Title": "A brand new bug",
        "System.State": "New",
        "System.WorkItemType": "Bug",
    },
    "relations": [],
}

PULL_REQUESTS: dict[str, Any] = {
    "value": [
        {
            "pullRequestId": 7,
            "title": "Fix the login form",
            "description": "Closes #42",
            "sourceRefName": "refs/heads/feature/login",
            "url": "https://dev.azure.com/acme/widgets/_apis/git/repositories/repo1/pullRequests/7",
            "createdBy": {"displayName": "Ada Lovelace"},
        },
        {
            "pullRequestId": 8,
            "title": "Unrelated change",
            "description": "No reference here",
            "sourceRefName": "refs/heads/main",
            "url": "https://dev.azure.com/acme/widgets/_apis/git/repositories/repo1/pullRequests/8",
        },
    ]
}


@dataclass
class RecordedRequest:
    """A request received by the stub server."""

    method: str
    path: str
    query: str
    body: Any
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class StubAzureDevOps:
    """The state of the stub server."""

    port: int = 0
    requests: list[RecordedRequest] = field(default_factory=list)

    @property
    def base_url(self) -> str:
        """The root URL of the stub server."""
        return f"http://127.0.0.1:{self.port}"

    @property
    def api_base_url(self) -> str:
        """The root URL of the REST API of the stub server."""
        return f"{self.base_url}/_apis"

    def record(
        self,
        method: str,
        path: str,
        query: str,
        body: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Store an incoming request."""
        self.requests.append(RecordedRequest(method, path, query, body, headers or {}))


class StubServer(ThreadingHTTPServer):
    """The HTTP server holding the state of the stub."""

    stub: StubAzureDevOps


class StubHandler(BaseHTTPRequestHandler):
    """Answers the few Azure DevOps endpoints used by the CLI."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        """Silence the default logging of the HTTP server."""

    # -- helpers ------------------------------------------------------------
    @property
    def stub(self) -> StubAzureDevOps:
        """The state of the stub server."""
        return cast(StubServer, self.server).stub

    def _headers(self) -> dict[str, str]:
        """The headers of the current request."""
        return dict(self.headers.items())

    def _read_body(self) -> Any:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except ValueError:
            return raw.decode(errors="replace")

    def _send(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- verbs --------------------------------------------------------------
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        self.stub.record("GET", path, parsed.query, None, self._headers())

        if path == "/_apis/wit/workitems/42":
            self._send(200, WORK_ITEM_42)
        elif path == "/_apis/wit/workitems/999":
            self._send(404, {"message": "Work item not found."})
        elif path == "/_apis/wit/workitems/401":
            self._send(401, {"message": "TF400813: The user is not authorized."})
        elif path == "/_apis/wit/workitems":
            self._send(200, {"value": [WORK_ITEM_42]})
        elif path == "/_apis/git/pullrequests":
            self._send(200, PULL_REQUESTS)
        else:
            self._send(404, {"message": f"Unknown route: {path}"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        self.stub.record("POST", path, parsed.query, body, self._headers())

        if path == "/_apis/wit/wiql":
            self._send(200, {"queryType": "flat", "workItems": [{"id": 42}]})
        elif path == "/_apis/wit/workitems/$Bug":
            self._send(200, WORK_ITEM_43)
        elif path == "/_apis/wit/workitems/42/comments":
            self._send(
                200,
                {
                    "id": 5,
                    "text": body.get("text") if isinstance(body, dict) else "",
                    "createdDate": "2026-10-21T10:00:00Z",
                    "createdBy": {"displayName": "Ada Lovelace"},
                    "url": "https://dev.azure.com/acme/widgets/_apis/wit/workItems/42/comments/5",
                },
            )
        else:
            self._send(404, {"message": f"Unknown route: {path}"})

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        self.stub.record("PATCH", path, parsed.query, body, self._headers())

        if path == "/_apis/wit/workitems/42":
            updated = json.loads(json.dumps(WORK_ITEM_42))
            for operation in body or []:
                field_name = str(operation.get("path", "")).replace("/fields/", "")
                if field_name:
                    updated["fields"][field_name] = operation.get("value")
            self._send(200, updated)
        else:
            self._send(404, {"message": f"Unknown route: {path}"})


def start_stub_server() -> tuple[StubAzureDevOps, StubServer]:
    """Start the stub server on a random free port."""
    server = StubServer(("127.0.0.1", 0), StubHandler)
    stub = StubAzureDevOps(port=server.server_address[1])
    server.stub = stub

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return stub, server
