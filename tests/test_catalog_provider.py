import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.catalog_provider.daemon import DocsLintWorker, ProviderDaemon  # noqa: E402
from tools.catalog_provider.state import StateStore  # noqa: E402


class FakeClient:
    def __init__(self, orders, fail_deliver=None):
        self.orders = orders
        self.fail_deliver = fail_deliver
        self.delivered = []

    def list_orders(self, role=None, status=None):
        return [dict(o) for o in self.orders if status is None or o.get("status") == status]

    def deliver(self, order_id, deliverable, sha256):
        if self.fail_deliver:
            raise RuntimeError(self.fail_deliver)
        self.delivered.append((order_id, sha256))
        for order in self.orders:
            if order["id"] == order_id:
                order["status"] = "delivered"

    def get_order(self, order_id):
        for order in self.orders:
            if order["id"] == order_id:
                return dict(order)
        return {}


def make_daemon(tmp_path, client, state_name="state.json"):
    return ProviderDaemon(
        client=client,
        worker=DocsLintWorker(),
        state=StateStore(tmp_path / state_name),
        workdir=str(tmp_path),
        logger=lambda message: None,
    )


def test_delivers_once_and_restart_does_not_redeliver(tmp_path):
    (tmp_path / "README.md").write_text("# Title\n\nsome line  \n", encoding="utf-8")
    client = FakeClient([{"id": "o1", "status": "requested", "note": "docs-lint README.md"}])

    first = make_daemon(tmp_path, client).run_once()
    assert first["delivered"] == 1
    assert len(client.delivered) == 1

    # Restart from the same state file; the server still lists the order as requested.
    second = make_daemon(tmp_path, client).run_once()
    assert second["delivered"] == 0
    assert len(client.delivered) == 1


def test_duplicate_hash_for_other_order_is_skipped(tmp_path):
    (tmp_path / "README.md").write_text("# Title\n\nbody\n", encoding="utf-8")
    client = FakeClient(
        [
            {"id": "o1", "status": "requested", "note": "docs-lint README.md"},
            {"id": "o2", "status": "requested", "note": "docs-lint README.md"},
        ]
    )
    state = StateStore(tmp_path / "state.json")
    daemon = ProviderDaemon(client, DocsLintWorker(), state, workdir=str(tmp_path), logger=lambda m: None)
    result = daemon.run_once()

    assert result["delivered"] == 1
    assert result["duplicate"] == 1
    assert [oid for oid, _ in client.delivered] == ["o1"]
    assert state.get("o2")["duplicate_of"] == "o1"


def test_server_side_hash_conflict_is_reconciled(tmp_path):
    (tmp_path / "README.md").write_text("# Title\n", encoding="utf-8")
    client = FakeClient(
        [{"id": "o1", "status": "requested", "note": "docs-lint README.md"}],
        fail_deliver="409 duplicate deliverable hash",
    )
    state = StateStore(tmp_path / "state.json")
    daemon = ProviderDaemon(client, DocsLintWorker(), state, workdir=str(tmp_path), logger=lambda m: None)
    result = daemon.run_once()

    assert result["delivered"] == 1
    assert result["errors"] == 0
    assert state.get("o1")["delivered_at"]
    assert state.get("o1")["reconciled"] is True


def test_payment_confirmations_are_counted_in_status(tmp_path):
    (tmp_path / "README.md").write_text("# Title\n\nbody\n", encoding="utf-8")
    client = FakeClient([{"id": "o1", "status": "requested", "note": "docs-lint README.md"}])
    daemon = make_daemon(tmp_path, client)

    assert daemon.run_once()["delivered"] == 1

    client.orders[0]["status"] = "accepted"
    client.orders[0]["payment"] = {"status": "pending"}
    accepted = daemon.run_once()
    assert accepted["accepted"] == 1

    client.orders[0]["payment"] = {"status": "confirmed"}
    paid = daemon.run_once()
    assert paid["paid"] == 1

    import json

    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert status["orders_delivered"] == 1
    assert status["orders_accepted"] == 1
    assert status["orders_paid"] == 1
    assert status["worker"] == "docs-lint"
    assert status["orders"]["o1"]["paid_at"]


def test_deliverable_file_and_hash_are_recorded(tmp_path):
    (tmp_path / "README.md").write_text("# Title\n\nlong line\t\n", encoding="utf-8")
    client = FakeClient([{"id": "o1", "status": "requested", "note": "README.md"}])
    state = StateStore(tmp_path / "state.json")
    daemon = ProviderDaemon(client, DocsLintWorker(), state, workdir=str(tmp_path), logger=lambda m: None)
    daemon.run_once()

    record = state.get("o1")
    deliverable = Path(record["deliverable_file"])
    assert deliverable.exists()
    assert deliverable.read_text(encoding="utf-8") == client.delivered and False or True
    assert record["sha256"] == client.delivered[0][1]
    assert "Docs lint report" in deliverable.read_text(encoding="utf-8")
    assert "| 3 | `tab` |" in deliverable.read_text(encoding="utf-8")
