"""Small standard-library smoke test for a running DeployLedger API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def get(base_url: str, path: str) -> object:
    request = urllib.request.Request(f"{base_url.rstrip('/')}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned {response.status}")
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    try:
        live = get(args.base_url, "/health/live")
        ready = get(args.base_url, "/health/ready")
        services = get(args.base_url, "/api/v1/services")
        dora = get(args.base_url, "/api/v1/metrics/dora")
    except (OSError, urllib.error.HTTPError, RuntimeError) as exc:
        print(f"smoke test failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"live": live, "ready": ready, "services": len(services), "dora": dora["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

