"""Container liveness probe for the SkyCast API."""

from __future__ import annotations

import os
from urllib.request import urlopen


def main() -> None:
    """Exit successfully when the API liveness endpoint responds."""
    port = os.getenv("PORT", "8000")
    with urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected health status: {response.status}")


if __name__ == "__main__":
    main()
