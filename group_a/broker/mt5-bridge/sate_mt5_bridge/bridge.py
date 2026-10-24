"""Demo adapter. Sync terminal calls run on a worker thread. Orders stay placeholders."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter

from sate_mt5_bridge.errors import AdapterError
from sate_mt5_bridge.frames import decode_frame, encode_frame
from sate_mt5_bridge.terminal import MockTerminal

DEMO_SESSIONS = 5
_APPROVED = frozenset({"Allow", "AllowWithSize"})
_CLOSED = frozenset({"DISCONNECTED", "UNAVAILABLE"})
_RECORD_OPS = {"positions": "positions", "fills": "fills", "fees": "fees"}


@dataclass
class Spec:
    min_lot: str
    lot_step: str
    stops_level: str
    settlement: str

    @property
    def complete(self) -> bool:
        return bool(self.min_lot and self.lot_step and self.stops_level)


@dataclass
class Placeholder:
    idempotency_key: str
    instrument: str
    side: str
    quantity: str
    verdict: str
    server_time: str
    protective_stop: str = ""
    broker_id: None = None
    state: str = "placeholder"
    stop_attached: bool = False


class Bridge:
    """SIM channel only. A LIVE socket is refused until a Windows host exists."""

    def __init__(self, terminal: MockTerminal, *, channel: str = "SIM") -> None:
        if channel != "SIM":
            raise AdapterError("live terminal is not provisioned", code="host")
        self.terminal = terminal
        self.channel = channel
        self.state = "DISCONNECTED"
        self.arm_halt: str | None = None
        self.spec = Spec("", "", "", "")
        self.quote: dict[str, object] = {}
        self.balance: dict[str, str] = {}
        self.orders: dict[str, Placeholder] = {}
        self.orders_enabled = False
        self.completed_sessions = 0
        self.ghost_submits = 0
        self.latency_us = 0
        self._login = ""
        self._server = ""
        self._instrument = ""
        self._sent: set[str] = set()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mt5-sync")

    def close(self) -> None:
        self._pool.shutdown(wait=True)

    def connect(
        self,
        expected_login: str,
        expected_server: str,
        grant: dict[str, object],
        *,
        instrument: str,
    ) -> str:
        self._require_grant(grant)
        self._login = expected_login
        self._server = expected_server
        self._instrument = instrument
        if self.state == "UNAVAILABLE":
            self.state = "RECONCILING"
        else:
            self.state = "AUTHENTICATING"
        try:
            return self._establish()
        except AdapterError as exc:
            self._fail(exc)
            raise

    def poll(self) -> str:
        """A-MOD-02. The kernel calls this on its own interval. The bridge does not pick one."""
        self._require_session()
        try:
            account = self._call("account", {})
            self._require_sim(account)
            if not self._fingerprint(account):
                self.state = "UNVERIFIED"
                self.arm_halt = "L2"
                return self.state
            self.arm_halt = None
            self._refresh()
            if self.state == "RECONCILING" and not self._sent_matches():
                return self.state
            self.state = "DEGRADED" if self._degraded() else "HEALTHY"
            return self.state
        except AdapterError as exc:
            self._fail(exc)
            raise

    def subscribe(self, instrument: str) -> dict[str, object]:
        self._require_session()
        try:
            self.quote = _require_quote(self._call("quote", {"instrument": instrument}))
        except AdapterError as exc:
            self._fail(exc)
            raise
        if self.state == "HEALTHY" and self._degraded():
            self.state = "DEGRADED"
        return self.quote

    def balances(self) -> dict[str, str]:
        self._require_session()
        try:
            self.balance = _require_balance(self._call("balance", {}))
        except AdapterError as exc:
            self._fail(exc)
            raise
        return self.balance

    def positions(self) -> list[dict[str, str]]:
        return self._records("positions")

    def fills(self) -> list[dict[str, str]]:
        return self._records("fills")

    def fees(self) -> list[dict[str, str]]:
        return self._records("fees")

    def order_status(self, idempotency_key: str) -> Placeholder:
        order = self.orders.get(idempotency_key)
        if order is None:
            raise AdapterError("the placeholder is unknown", code="status")
        return order

    def disconnect(self) -> None:
        if self.state == "HEALTHY":
            self.completed_sessions += 1
        self.state = "DISCONNECTED"

    def crash(self) -> None:
        """BF-A1. The terminal drops. Existing placeholders are not sent again."""
        self.terminal.alive = False
        self.state = "UNAVAILABLE"

    def place_placeholder(
        self,
        *,
        verdict: str,
        idempotency_key: str,
        instrument: str,
        side: str,
        quantity: object,
        reduce_only: bool,
        protective_stop: str = "",
    ) -> Placeholder:
        if self.state != "HEALTHY":
            raise AdapterError("the adapter is not healthy", code="state")
        if verdict not in _APPROVED:
            raise AdapterError("no terminal order without an allow verdict", code="verdict")
        if not idempotency_key:
            raise AdapterError("an idempotency key is required", code="idempotency")
        existing = self.orders.get(idempotency_key)
        if existing is not None:
            return existing
        if not reduce_only and not self.spec.complete:
            raise AdapterError("the contract spec has not been reported", code="spec")
        if not reduce_only and not protective_stop:
            raise AdapterError("every entry carries a broker-side stop", code="protective_stop")
        if not self.orders_enabled:
            raise AdapterError("an unknown settlement rule stays disabled", code="settlement")
        amount = _money(quantity)
        if not amount:
            raise AdapterError("quantity stays a decimal string", code="malformed")
        if idempotency_key in self._sent:
            self.ghost_submits += 1
            raise AdapterError("the placeholder was already sent", code="ghost")
        try:
            reply = self._call(
                "order",
                {
                    "idempotency_key": idempotency_key,
                    "instrument": instrument,
                    "side": side,
                    "quantity": amount,
                    "verdict": verdict,
                    "protective_stop": protective_stop,
                    "reduce_only": reduce_only,
                },
            )
        except AdapterError as exc:
            self._fail(exc)
            raise
        self._sent.add(idempotency_key)
        server_time = reply.get("server_time")
        if not isinstance(server_time, str) or not server_time:
            self.state = "UNVERIFIED"
            raise AdapterError("broker events carry a server time", code="malformed")
        stop_attached = reply.get("stop_attached") is True
        if not reduce_only and not stop_attached:
            raise AdapterError("the broker-side stop was not verified", code="protective_stop")
        order = Placeholder(
            idempotency_key=idempotency_key,
            instrument=instrument,
            side=side,
            quantity=amount,
            verdict=verdict,
            server_time=server_time,
            protective_stop=protective_stop,
            stop_attached=stop_attached,
        )
        self.orders[idempotency_key] = order
        return order

    def withdraw(self) -> None:
        raise AdapterError("withdrawals stay on the manual owner path", code="manual")

    def gate_met(self) -> bool:
        return (
            self.channel == "SIM"
            and self.completed_sessions >= DEMO_SESSIONS
            and self.ghost_submits == 0
        )

    def _establish(self) -> str:
        account = self._call("account", {})
        self._require_sim(account)
        if not self._fingerprint(account):
            self.state = "UNVERIFIED"
            self.arm_halt = "L2"
            return self.state
        self.arm_halt = None
        self._refresh()
        if self.state == "RECONCILING" and not self._sent_matches():
            return self.state
        self.state = "DEGRADED" if self._degraded() else "HEALTHY"
        return self.state

    def _refresh(self) -> None:
        spec = self._call("spec", {"instrument": self._instrument})
        self.spec = Spec(
            _money(spec.get("min_lot")),
            _money(spec.get("lot_step")),
            _money(spec.get("stops_level")),
            _label(spec.get("settlement")),
        )
        self.orders_enabled = self.spec.settlement not in {"", "unknown"}
        quote = self._call("quote", {"instrument": self._instrument})
        self.quote = _require_quote(quote)
        self.balance = _require_balance(self._call("balance", {}))

    def _sent_matches(self) -> bool:
        reported = self._call("orders", {})
        keys = reported.get("idempotency_keys")
        if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
            raise AdapterError("the terminal order list is malformed", code="malformed")
        return sorted(keys) == sorted(self._sent)

    def _fingerprint(self, account: dict[str, object]) -> bool:
        login = account.get("login")
        server = account.get("server")
        if not isinstance(login, str) or not isinstance(server, str):
            return False
        if _has_whitespace(login) or _has_whitespace(server):
            return False
        if _has_whitespace(self._login) or _has_whitespace(self._server):
            return False
        return login == self._login and server == self._server

    def _require_sim(self, account: dict[str, object]) -> None:
        if account.get("mode") != "SIM":
            self.state = "UNVERIFIED"
            raise AdapterError(
                "live credentials are refused on the sim channel",
                code="live_on_sim",
            )

    def _degraded(self) -> bool:
        return (
            not self.quote.get("fresh")
            or not self.quote.get("heartbeat_ok")
            or bool(self.quote.get("rate_limited"))
        )

    def _require_session(self) -> None:
        if self.state in _CLOSED or not self._login:
            raise AdapterError("the adapter has no session", code="state")

    def _records(self, op: str) -> list[dict[str, str]]:
        self._require_session()
        try:
            raw = self._call(op, {})
        except AdapterError as exc:
            self._fail(exc)
            raise
        rows = raw.get(_RECORD_OPS[op])
        if not isinstance(rows, list):
            raise AdapterError("the terminal record list is malformed", code="malformed")
        records: list[dict[str, str]] = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("server_time"):
                raise AdapterError("broker events carry a server time", code="malformed")
            record: dict[str, str] = {}
            for key, value in row.items():
                if not isinstance(key, str) or not isinstance(value, str) or not value:
                    raise AdapterError("broker records stay strings", code="malformed")
                record[key] = value
            records.append(record)
        return records

    def _require_grant(self, grant: dict[str, object]) -> None:
        if grant.get("group") != "A":
            raise AdapterError("the bridge stays on group A", code="scope")
        if "password" in grant or "secret" in grant:
            raise AdapterError("the bridge does not accept credentials", code="credential")
        if grant.get("injected") is not True:
            raise AdapterError("the kernel has not injected a credential", code="credential")

    def _fail(self, exc: AdapterError) -> None:
        if exc.code == "disconnect":
            self.state = "UNAVAILABLE"
        elif exc.code == "malformed":
            self.state = "UNVERIFIED"

    def _call(self, op: str, payload: dict[str, object]) -> dict[str, object]:
        frame = encode_frame(op, payload)
        started = perf_counter()

        def work() -> bytes:
            request = decode_frame(frame)
            body = request["payload"]
            if not isinstance(body, dict):
                raise AdapterError("the bridge frame is malformed", code="malformed")
            reply = self.terminal.handle(str(request["op"]), body)
            return encode_frame("reply", reply)

        raw = self._pool.submit(work).result()
        self.latency_us = int((perf_counter() - started) * 1_000_000)
        decoded = decode_frame(raw)
        reply = decoded["payload"]
        if not isinstance(reply, dict):
            raise AdapterError("the bridge frame is malformed", code="malformed")
        return reply


def _require_quote(payload: dict[str, object]) -> dict[str, object]:
    bid = _money(payload.get("bid"))
    ask = _money(payload.get("ask"))
    server_time = payload.get("server_time")
    if not bid or not ask or not isinstance(server_time, str) or not server_time:
        raise AdapterError("a quote needs prices and a server time", code="malformed")
    if not isinstance(payload.get("fresh"), bool):
        raise AdapterError("a quote needs a freshness flag", code="malformed")
    if not isinstance(payload.get("heartbeat_ok"), bool):
        raise AdapterError("a quote needs a heartbeat flag", code="malformed")
    return {
        "instrument": payload.get("instrument"),
        "bid": bid,
        "ask": ask,
        "server_time": server_time,
        "fresh": payload["fresh"],
        "heartbeat_ok": payload["heartbeat_ok"],
        "rate_limited": bool(payload.get("rate_limited")),
    }


def _require_balance(payload: dict[str, object]) -> dict[str, str]:
    server_time = payload.get("server_time")
    if not isinstance(server_time, str) or not server_time:
        raise AdapterError("broker events carry a server time", code="malformed")
    return {
        "equity": _money(payload.get("equity")),
        "margin": _money(payload.get("margin")),
        "currency": _label(payload.get("currency")),
        "server_time": server_time,
    }


def _money(value: object) -> str:
    if not isinstance(value, str):
        raise AdapterError("broker amounts stay decimal strings", code="malformed")
    if value and not _is_decimal(value):
        raise AdapterError("broker amounts stay decimal strings", code="malformed")
    return value


def _label(value: object) -> str:
    if not isinstance(value, str):
        raise AdapterError("broker fields stay strings", code="malformed")
    return value


def _is_decimal(value: str) -> bool:
    if value.endswith("."):
        return False
    whole, dot, frac = value.partition(".")
    if not whole.isdigit() or (dot and not frac.isdigit()):
        return False
    return whole == "0" or not whole.startswith("0")


def _has_whitespace(value: str) -> bool:
    return (not value) or any(character.isspace() for character in value)
