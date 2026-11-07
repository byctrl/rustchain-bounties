"""Run the provider daemon.

    python -m tools.catalog_provider --worker docs-lint --listing <id> --repo .
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .client import make_client
from .daemon import CatalogProvider
from .state import ProviderState
from .workers import WorkerError, available_workers, build_worker


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m tools.catalog_provider",
        description="Unattended provider for the RustChain RTC service catalog.",
    )
    parser.add_argument("--listing", default=os.environ.get("CATALOG_LISTING_ID", ""),
                        help="listing id to serve (default: $CATALOG_LISTING_ID)")
    parser.add_argument("--worker", default=os.environ.get("CATALOG_WORKER", "docs-lint"),
                        help="worker to run: %s" % ", ".join(available_workers()))
    parser.add_argument("--repo", default=os.environ.get("CATALOG_REPO_PATH") or None,
                        help="local repository path the worker should inspect")
    parser.add_argument("--base-url", default=None, help="catalog base URL")
    parser.add_argument("--token", default=None, help="catalog auth token")
    parser.add_argument("--state", default=os.environ.get("CATALOG_STATE_PATH", "catalog_provider_state.json"),
                        help="on-disk state file")
    parser.add_argument("--out-dir", default="deliverables", help="where deliverables are written")
    parser.add_argument("--status", default="status.json", help="path for status.json")
    parser.add_argument("--interval", type=float, default=60.0, help="seconds between ticks")
    parser.add_argument("--max-attempts", type=int, default=3, help="attempts before an order is parked")
    parser.add_argument("--once", action="store_true", help="run exactly one tick and exit")
    parser.add_argument("--ticks", type=int, default=0, help="run N ticks then exit (0 = forever)")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        worker = build_worker(args.worker)
    except WorkerError as exc:
        sys.stderr.write("%s\n" % exc)
        return 2

    client = make_client(base_url=args.base_url, token=args.token)
    state = ProviderState(args.state)
    provider = CatalogProvider(
        client=client,
        worker=worker,
        state=state,
        listing=args.listing or None,
        repo_path=args.repo,
        out_dir=args.out_dir,
        status_path=args.status,
        interval=args.interval,
        max_attempts=args.max_attempts,
    )

    if args.once:
        provider.recover()
        print(json.dumps(provider.tick(), sort_keys=True))
        return 0
    if args.ticks:
        provider.run_forever(max_ticks=args.ticks)
        return 0
    provider.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
