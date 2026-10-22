"""Value object: the kind of a related link."""

from __future__ import annotations

from enum import StrEnum


class LinkKind(StrEnum):
    """The kind of artifact a work item is linked to."""

    PULL_REQUEST = "pull_request"
    BRANCH = "branch"
    COMMIT = "commit"
    WORK_ITEM = "work_item"
    OTHER = "other"
