"""Tests for tools/catalog_provider (stdlib unittest, pytest-compatible)."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.catalog_provider.client import CatalogError, sha256_text
from tools.catalog_provider.daemon import CatalogProvider, payment_status
from tools.catalog_provider.state import ProviderState
from tools.catalog_provider.workers import (
    CodeReviewWorker,
    Deliverable,
    DocsLintWorker,
    WorkerError,
    build_worker,
)


class FakeClient:
    def __init__(self, orders, payment="pending", conflict=False, order_status="requested"):
        self.orders = list(orders)
        self.payment = payment
        self.conflict = conflict
        self.order_status = order_status
        self.deliveries = []
        self.list_calls = 0
        self.get_calls = 0

    def list_orders(self, role="provider", status="requested"):
        self.list_calls += 1
        return list(self.orders)

    def get_order(self, oid):
        self.get_calls += 1
        for order in self.orders:
            if str(order.get("id")) == str(oid):
                out = dict(order)
                out["status"] = self.order_status
                out["payment"] = {"status": self.payment}
                return out
        return {}

    def deliver(self, oid, text, digest=None):
        if self.conflict:
            raise CatalogError("conflict", status=409)
        self.deliveries.append((str(oid), text, digest or sha256_text(text)))
        return {"ok": True}


class StubWorker:
    name = "stub"
    category = "testing"

    def __init__(self, fail=False):
        self.fail = fail

    def run(self, order, repo_path=None):
        if self.fail:
            raise WorkerError("cannot do it")
        return Deliverable(text="# report\n\norder %s\n" % order.get("id"), filename="report.md")


class ProviderTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="catalog-provider-")
        self.state = ProviderState(os.path.join(self.tmp, "state.json"))
        self.status = os.path.join(self.tmp, "status.json")
        self.out = os.path.join(self.tmp, "deliverables")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def provider(self, client, worker=None, listing=None):
        return CatalogProvider(
            client=client,
            worker=worker or StubWorker(),
            state=self.state,
            listing=listing,
            out_dir=self.out,
            status_path=self.status,
            sleep=lambda seconds: None,
        )

    def test_sha256_is_stable(self):
        self.assertEqual(sha256_text("abc"), sha256_text("abc"))
        self.assertNotEqual(sha256_text("abc"), sha256_text("abd"))

    def test_payment_status_reads_nested_and_flat(self):
        self.assertEqual(payment_status({"payment": {"status": "Confirmed"}}), "confirmed")
        self.assertEqual(payment_status({"payment_status": "paid"}), "paid")
        self.assertEqual(payment_status({}), "")

    def test_state_survives_reload(self):
        self.state.mark("o1", status="delivered", deliverable_sha256="abc")
        reloaded = ProviderState(self.state.path)
        self.assertEqual(reloaded.order("o1")["status"], "delivered")
        self.assertEqual(reloaded.counts()["delivered"], 1)
        self.assertTrue(reloaded.already_delivered("o1", "abc"))

    def test_delivers_once_and_never_twice(self):
        client = FakeClient([{"id": "o1"}])
        provider = self.provider(client)
        first = provider.tick()
        self.assertEqual(first["delivered"], 1)
        self.assertEqual(len(client.deliveries), 1)
        self.assertEqual(client.deliveries[0][2], sha256_text(client.deliveries[0][1]))
        second = provider.tick()
        self.assertEqual(second["delivered"], 0)
        self.assertEqual(second["duplicate"], 1)
        self.assertEqual(len(client.deliveries), 1)

    def test_conflict_marks_delivered(self):
        client = FakeClient([{"id": "o1"}], conflict=True)
        provider = self.provider(client)
        summary = provider.tick()
        self.assertEqual(summary["duplicate"], 1)
        self.assertEqual(self.state.order("o1")["status"], "delivered")

    def test_listing_filter_skips_other_listings(self):
        client = FakeClient(
            [{"id": "o1", "listing_id": "other"}, {"id": "o2", "listing_id": "mine"}]
        )
        provider = self.provider(client, listing="mine")
        provider.tick()
        self.assertEqual([entry[0] for entry in client.deliveries], ["o2"])

    def test_worker_failure_parks_the_order(self):
        client = FakeClient([{"id": "o1"}])
        provider = self.provider(client, worker=StubWorker(fail=True))
        for _ in range(4):
            provider.tick()
        record = self.state.order("o1")
        self.assertEqual(record["status"], "failed")
        self.assertGreaterEqual(record["attempts"], 3)
        self.assertEqual(client.deliveries, [])

    def test_payment_confirmation_updates_status_json(self):
        client = FakeClient([{"id": "o1"}])
        provider = self.provider(client)
        first = provider.tick()
        self.assertEqual(first["delivered"], 1)
        self.assertEqual(first["paid"], 0)
        client.payment = "confirmed"
        second = provider.tick()
        self.assertEqual(second["paid"], 1)
        self.assertEqual(self.state.order("o1")["status"], "paid")
        with open(self.status, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["counts"]["paid"], 1)
        self.assertEqual(payload["worker"], "stub")

    def test_recover_returns_interrupted_order_to_queue(self):
        self.state.mark("o1", status="delivering")
        client = FakeClient([{"id": "o1"}])
        provider = self.provider(client)
        self.assertEqual(provider.recover(), 1)
        self.assertEqual(self.state.order("o1")["status"], "requested")

    def test_docs_lint_worker_reports_findings(self):
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# Title \n\n[missing](nope.md)\n")
        worker = DocsLintWorker()
        deliverable = worker.run({"id": "o1", "note": repo})
        self.assertIn("Documentation lint report", deliverable.text)
        self.assertIn("trailing-whitespace", deliverable.text)
        self.assertIn("broken-link", deliverable.text)
        self.assertEqual(deliverable.text, worker.run({"id": "o1", "note": repo}).text)

    def test_code_review_worker_is_deterministic(self):
        repo = os.path.join(self.tmp, "repo2")
        os.makedirs(repo)
        with open(os.path.join(repo, "main.py"), "w", encoding="utf-8") as fh:
            fh.write("# TODO: tidy\nprint(1)\n")
        worker = CodeReviewWorker()
        first = worker.run({"id": "o1", "note": repo}).text
        second = worker.run({"id": "o1", "note": repo}).text
        self.assertEqual(first, second)
        self.assertIn("TODO", first)

    def test_worker_requires_a_readable_repo(self):
        with self.assertRaises(WorkerError):
            DocsLintWorker().run({"id": "o1", "note": "definitely/not/here"})

    def test_build_worker_unknown_name(self):
        self.assertEqual(build_worker("docs-lint").name, "docs-lint")
        with self.assertRaises(WorkerError):
            build_worker("does-not-exist")


if __name__ == "__main__":
    unittest.main()
