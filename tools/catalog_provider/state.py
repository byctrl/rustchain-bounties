'''Durable provider state so a restart never double-delivers.'''
import json
import os
import tempfile
from pathlib import Path

class State:
    def __init__(self, path):
        self.path = Path(path)
        self.orders = {}
        self.load()
    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {}
        self.orders = dict(data.get('orders') or {})
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {'orders': self.orders}
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix='.state-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
            os.replace(tmp, str(self.path))
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    def get(self, order_id):
        return self.orders.get(str(order_id))
    def record(self, order_id, **fields):
        key = str(order_id)
        current = dict(self.orders.get(key) or {})
        current.update(fields)
        self.orders[key] = current
        self.save()
        return current
