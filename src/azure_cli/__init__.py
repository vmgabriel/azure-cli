"""azure-cli — a CLI to interact with Azure DevOps work items.

The package is split in four layers that only depend on each other in one
direction:

``domain``          the business rules (work items, states, tags, ports)
``application``     the use cases built on top of those rules
``infrastructure``  the adapters talking to the Azure DevOps REST API
``presentation``    the Typer commands the user interacts with
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
