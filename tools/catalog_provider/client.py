'''Minimal stdlib client for the RustChain RTC service catalog.'''
import hashlib, hmac, json, secrets, time
import urllib.error, urllib.parse, urllib.request

DEFAULT_BASE_URL = 'https://rustchain.org'

class CatalogError(RuntimeError):
    pass

class CatalogHTTPError(CatalogError):
    def __init__(self, status, body):
        super().__init__('catalog request failed with HTTP %s: %s' % (status, (body or '')[:200]))
        self.status = status
        self.body = body or ''

def _order_id(order):
    for key in ('id', 'order_id', 'orderId', 'uuid'):
        value = order.get(key)
        if value:
            return str(value)
    return None

def _note(order):
    for key in ('note', 'notes', 'details', 'description', 'instructions'):
        value = order.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ''

def _status(order):
    return str(order.get('status') or '').strip().lower()

def _payment(order):
    value = order.get('payment') or order.get('payment_status') or order.get('pay')
    if isinstance(value, dict):
        value = value.get('status') or value.get('state') or ''
    return str(value).strip().lower()

def _orders(payload):
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, dict):
        for key in ('orders', 'items', 'data', 'results'):
            value = payload.get(key)
            if isinstance(value, list):
                return list(value)
    return []

class CatalogClient:
    def __init__(self, base_url=DEFAULT_BASE_URL, wallet_id='', secret_key='', timeout=30.0):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip('/')
        self.wallet_id = wallet_id or ''
        self.secret_key = secret_key or ''
        self.timeout = float(timeout)

    def _sign(self, method, path, body, timestamp, nonce):
        digest = hashlib.sha256(body or b'').hexdigest()
        message = '\n'.join([method.upper(), path, timestamp, nonce, digest])
        return hmac.new(self.secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

    def request(self, method, path, params=None, body=None):
        url = self.base_url + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        payload = json.dumps(body, sort_keys=True).encode('utf-8') if body is not None else None
        req = urllib.request.Request(url, data=payload, method=method.upper())
        req.add_header('Accept', 'application/json')
        req.add_header('User-Agent', 'rustchain-catalog-provider/1.0')
        if payload is not None:
            req.add_header('Content-Type', 'application/json')
        if self.secret_key:
            stamp = str(int(time.time()))
            nonce = secrets.token_hex(16)
            req.add_header('X-RC-Wallet', self.wallet_id)
            req.add_header('X-RC-Timestamp', stamp)
            req.add_header('X-RC-Nonce', nonce)
            req.add_header('X-RC-Signature', self._sign(method, path, payload, stamp, nonce))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise CatalogHTTPError(exc.code, exc.read().decode('utf-8', 'replace')) from None
        except urllib.error.URLError as exc:
            raise CatalogError('catalog request failed: %s' % exc) from None
        if not raw:
            return {}
        try:
            return json.loads(raw.decode('utf-8'))
        except json.JSONDecodeError as exc:
            raise CatalogError('catalog returned non-JSON payload: %s' % exc) from None

    def list_orders(self, role='provider', status='requested'):
        return _orders(self.request('GET', '/catalog/orders', params={'role': role, 'status': status}))

    def get_order(self, order_id):
        payload = self.request('GET', '/catalog/orders/%s' % urllib.parse.quote(str(order_id), safe=''))
        if isinstance(payload, dict) and isinstance(payload.get('order'), dict):
            return dict(payload['order'])
        return dict(payload) if isinstance(payload, dict) else {}

    def deliver(self, order_id, content, sha256, filename, media_type='text/markdown', note=''):
        body = {'deliverable': content, 'sha256': sha256, 'filename': filename}
        if media_type:
            body['media_type'] = media_type
        if note:
            body['note'] = note
        return self.request('POST', '/catalog/orders/%s/deliver' % urllib.parse.quote(str(order_id), safe=''), body=body)
