'''Unattended provider daemon for the RustChain RTC service catalog.'''
import argparse
import hashlib
import json
import logging
import signal
import sys
import time
from pathlib import Path

from .client import CatalogClient, CatalogHTTPError, _order_id, _status, _payment, _note
from .state import State
from .workers import CodeReviewWorker, DocsLintWorker

LOG = logging.getLogger('catalog_provider')
WORKERS = {'docs-lint': DocsLintWorker, 'code-review': CodeReviewWorker}

class Provider:
    def __init__(self, client, state, worker, workdir, poll_interval=15.0, payment_interval=30.0):
        self.client = client
        self.state = state
        self.worker = worker
        self.workdir = Path(workdir)
        self.poll_interval = float(poll_interval)
        self.payment_interval = float(payment_interval)
        self.running = True
        self.counters = {'delivered': 0, 'accepted': 0, 'paid': 0, 'failed': 0}
    def stop(self, *args):
        self.running = False
    def tick(self):
        for order in self.client.list_orders('provider', 'requested'):
            if not self.running:
                return
            oid = _order_id(order)
            if not oid:
                continue
            entry = self.state.get(oid) or {}
            if entry.get('delivered') or entry.get('sha256'):
                continue
            self.deliver(order, oid)
    def deliver(self, order, oid):
        note = _note(order)
        try:
            deliverable = self.worker.work(order)
        except Exception as exc:
            LOG.exception('worker failed for order %s', oid)
            self.state.record(oid, status='worker_error', error=str(exc))
            self.counters['failed'] += 1
            return
        content = deliverable.content
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        out_dir = self.workdir / 'deliverables' / oid
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / deliverable.filename
        out_file.write_text(content, encoding='utf-8')
        try:
            self.client.deliver(oid, content, digest, deliverable.filename, deliverable.media_type, note)
            self.state.record(oid, status='delivered', sha256=digest, delivered=True, path=str(out_file), note=note)
            self.counters['delivered'] += 1
            LOG.info('delivered order %s sha256=%s', oid, digest)
        except CatalogHTTPError as exc:
            if exc.status in (409, 422):
                LOG.warning('order %s already delivered (HTTP %s); recording', oid, exc.status)
                self.state.record(oid, status='delivered', sha256=digest, delivered=True, path=str(out_file), duplicate=True)
            else:
                LOG.error('deliver failed for %s: %s', oid, exc)
                self.state.record(oid, status='deliver_error', error=str(exc))
                self.counters['failed'] += 1
        except Exception as exc:
            LOG.exception('deliver failed for %s', oid)
            self.state.record(oid, status='deliver_error', error=str(exc))
            self.counters['failed'] += 1
    def watch_payments(self):
        for oid, entry in list(self.state.orders.items()):
            if not entry.get('delivered') or entry.get('paid'):
                continue
            try:
                order = self.client.get_order(oid)
            except Exception as exc:
                LOG.warning('payment poll failed for %s: %s', oid, exc)
                continue
            status = _status(order)
            payment = _payment(order)
            if status in ('accepted', 'completed') and not entry.get('accepted'):
                self.state.record(oid, accepted=True, accepted_status=status)
                self.counters['accepted'] += 1
                LOG.info('order %s accepted', oid)
            if payment == 'confirmed' or status == 'paid':
                self.state.record(oid, paid=True, payment=payment or 'confirmed')
                self.counters['paid'] += 1
                LOG.info('order %s paid', oid)
    def write_status(self):
        payload = {'counters': self.counters, 'orders': len(self.state.orders), 'updated': int(time.time())}
        status_path = self.workdir / 'status.json'
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    def run(self, once=False):
        last_payment = 0.0
        while self.running:
            try:
                self.tick()
                now = time.time()
                if now - last_payment >= self.payment_interval:
                    self.watch_payments()
                    last_payment = now
                self.write_status()
            except Exception:
                LOG.exception('provider loop error')
            if once:
                break
            time.sleep(self.poll_interval)

def build_parser():
    parser = argparse.ArgumentParser(description='Unattended RustChain catalog provider')
    parser.add_argument('--category', default='docs-lint', choices=sorted(WORKERS))
    parser.add_argument('--base-url', default='https://rustchain.org')
    parser.add_argument('--wallet-id', default='')
    parser.add_argument('--secret-key', default='')
    parser.add_argument('--workdir', default='.catalog-provider')
    parser.add_argument('--poll-interval', type=float, default=15.0)
    parser.add_argument('--payment-interval', type=float, default=30.0)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    return parser

def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    workdir = Path(args.workdir).resolve()
    state = State(workdir / 'state.json')
    client = CatalogClient(args.base_url, args.wallet_id, args.secret_key)
    worker = WORKERS[args.category](workdir)
    provider = Provider(client, state, worker, workdir, args.poll_interval, args.payment_interval)
    signal.signal(signal.SIGINT, provider.stop)
    signal.signal(signal.SIGTERM, provider.stop)
    LOG.info('catalog provider started category=%s workdir=%s', args.category, workdir)
    provider.run(once=args.once)
    return 0

if __name__ == '__main__':
    sys.exit(main())
