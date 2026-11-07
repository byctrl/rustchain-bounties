"""``python3 -m tools.catalog_provider`` entry point."""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from .daemon import DocsLintWorker, ProviderDaemon, Worker
from .state import StateStore

WORKERS = {"docs-lint": DocsLintWorker}


class CatalogCliAdapter:
    """Thin shim over ``tools.catalog_cli``'s client (auth lives there)."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def _method(self, *names: str) -> Any:
        for name in names:
            func = getattr(self._client, name, None)
            if callable(func):
                return func
        raise AttributeError("catalog client has none of: %s" % ", ".join(names))

    def list_orders(self, role: str = "provider", status: Optional[str] = None) -> Any:
        kwargs: dict = {"role": role}
        if status is not None:
            kwargs["status"] = status
        return self._method("list_orders", "get_orders")(**kwargs)

    def deliver(self, order_id: str, deliverable: str, sha256: str) -> Any:
        return self._method("deliver", "deliver_order")(
            order_id=order_id, deliverable=deliverable, sha256=sha256
        )

    def get_order(self, order_id: str) -> Any:
        return self._method("get_order", "order")(order_id=order_id)


def build_client() -> CatalogCliAdapter:
    """Reuse ``tools/catalog_cli.py``'s authenticated client; never re-auth here."""
    try:
        from tools.catalog_cli import CatalogClient  # type: ignore
    except Exception as exc:  # pragma: no cover - needs the Rustchain checkout
        raise SystemExit(
            "tools/catalog_cli.py is required for authenticated calls (%s). "
            "Run this from a Rustchain checkout." % exc
        )
    return CatalogCliAdapter(CatalogClient())


def build_worker(name: str) -> Worker:
    try:
        return WORKERS[name]()
    except KeyError:
        raise SystemExit("unknown worker %r (choose from %s)" % (name, ", ".join(sorted(WORKERS))))


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Unattended RTC catalog provider")
    parser.add_argument("--state", default="catalog_provider/state.json", help="delivery state file")
    parser.add_argument("--status", default=None, help="status.json path (default: next to --state)")
    parser.add_argument("--workdir", default=".", help="directory the worker reads orders against")
    parser.add_argument("--listing-id", default=None, help="only serve this listing")
    parser.add_argument("--poll-interval", type=float, default=30.0)
    parser.add_argument("--worker", default="docs-lint", choices=sorted(WORKERS))
    parser.add_argument("--once", action="store_true", help="single pass, then exit")
    args = parser.parse_args(argv)

    daemon = ProviderDaemon(
        client=build_client(),
        worker=build_worker(args.worker),
        state=StateStore(args.state),
        listing_id=args.listing_id,
        workdir=args.workdir,
        status_path=args.status,
        poll_interval=args.poll_interval,
    )
    if args.once:
        print(json.dumps(daemon.run_once(), sort_keys=True))
        return 0
    daemon.run_forever()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
