# catalog_provider

Unattended provider for the RTC service catalog:
<https://rustchain.org/catalog> (`docs/SERVICE_CATALOG.md`).

It lists work, watches its own requested orders, does the work, delivers it and
waits to be paid -- no human in the loop. Non-custodial: the buyer pays from
their own wallet with memo `svc: `, the provider never holds funds.

## Run

```bash
python3 -m tools.catalog_provider \
  --worker docs-lint \
  --listing <your-listing-id> \
  --repo /path/to/repo \
  --state catalog_provider_state.json \
  --status status.json
```

Environment: `RUSTCHAIN_CATALOG_URL`, `RUSTCHAIN_CATALOG_TOKEN`,
`CATALOG_LISTING_ID`, `CATALOG_WORKER`, `CATALOG_REPO_PATH`,
`CATALOG_STATE_PATH`.

## What one tick does

1. `GET /catalog/orders?role=provider&status=requested`, filtered to `--listing`.
2. Runs the worker, writes the markdown deliverable to `--out-dir`, computes its
   sha256 and calls `POST /catalog/orders/<id>/deliver`.
3. Polls every delivered order until payment is `confirmed`, then records it as
   `paid`.

## Restart safety

Every order is recorded in `--state` before delivery, written with an atomic
replace. On start-up `recover()` re-reads any order left in `delivering` and
either marks it delivered (the server already has it) or puts it back in the
queue. A server-side HTTP 409 means the deliverable hash already exists, which
is treated as success instead of a retry loop.

## status.json

```json
{
  "listing": "...",
  "worker": "docs-lint",
  "category": "docs",
  "updated_at": "2026-01-01T00:00:00Z",
  "counts": {"requested": 0, "delivered": 1, "accepted": 0, "paid": 2},
  "orders": [{"order_id": "...", "status": "paid", "payment_status": "confirmed"}]
}
```

## Workers

* `docs-lint` (category `docs`) -- markdown lint: missing titles, trailing
  whitespace, tabs, very long lines, broken relative links.
* `code-review` (category `review`) -- deterministic static pass: file types,
  TODO/FIXME markers, README/LICENSE/tests checklist.

Both are stdlib-only and deterministic. A worker is any object with `name`,
`category` and `run(order, repo_path=None) -> Deliverable`, so an API-model
reviewer can be dropped in without touching the daemon.

## Tests

```bash
python3 -m pytest -q tools/catalog_provider/test_catalog_provider.py
```
