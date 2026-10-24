"""In-process demo terminal. It stands in for MT5 while the Windows host is undecided."""

from __future__ import annotations

from sate_mt5_bridge.errors import AdapterError


class MockTerminal:
    """Reports the fields the adapter must normalise. It does not choose a lot size."""

    def __init__(
        self,
        *,
        login: str,
        server: str,
        mode: str,
        bid: str,
        ask: str,
        server_time: str,
        fresh: bool = True,
        heartbeat_ok: bool = True,
        rate_limited: bool = False,
        min_lot: str = "",
        lot_step: str = "",
        stops_level: str = "",
        settlement: str = "demo",
        equity: str = "",
        margin: str = "",
        currency: str = "",
        stop_attach_fails: bool = False,
    ) -> None:
        self.login = login
        self.server = server
        self.mode = mode
        self.bid = bid
        self.ask = ask
        self.server_time = server_time
        self.fresh = fresh
        self.heartbeat_ok = heartbeat_ok
        self.rate_limited = rate_limited
        self.min_lot = min_lot
        self.lot_step = lot_step
        self.stops_level = stops_level
        self.settlement = settlement
        self.equity = equity
        self.margin = margin
        self.currency = currency
        self.positions: list[dict[str, str]] = []
        self.fills: list[dict[str, str]] = []
        self.fees: list[dict[str, str]] = []
        self.alive = True
        self.stop_attach_fails = stop_attach_fails
        self.submits: list[str] = []
        self.attached_stops: list[str] = []

    def handle(self, op: str, payload: dict[str, object]) -> dict[str, object]:
        if not self.alive:
            raise AdapterError("the terminal is disconnected", code="disconnect")
        if op == "account":
            return {"login": self.login, "server": self.server, "mode": self.mode}
        if op == "quote":
            return {
                "instrument": payload["instrument"],
                "bid": self.bid,
                "ask": self.ask,
                "server_time": self.server_time,
                "fresh": self.fresh,
                "heartbeat_ok": self.heartbeat_ok,
                "rate_limited": self.rate_limited,
            }
        if op == "spec":
            return {
                "instrument": payload["instrument"],
                "min_lot": self.min_lot,
                "lot_step": self.lot_step,
                "stops_level": self.stops_level,
                "settlement": self.settlement,
            }
        if op == "balance":
            return {
                "equity": self.equity,
                "margin": self.margin,
                "currency": self.currency,
                "server_time": self.server_time,
            }
        if op == "positions":
            return {"positions": [dict(row) for row in self.positions]}
        if op == "fills":
            return {"fills": [dict(row) for row in self.fills]}
        if op == "fees":
            return {"fees": [dict(row) for row in self.fees]}
        if op == "orders":
            return {"idempotency_keys": list(self.submits)}
        if op == "order":
            key = str(payload["idempotency_key"])
            reduce_only = payload.get("reduce_only") is True
            stop = payload.get("protective_stop")
            if not reduce_only and (not isinstance(stop, str) or not stop):
                raise AdapterError("every entry carries a broker-side stop", code="protective_stop")
            if self.stop_attach_fails:
                raise AdapterError("the broker refused the protective stop", code="protective_stop")
            self.submits.append(key)
            self.attached_stops.append(stop)
            return {
                "idempotency_key": key,
                "broker_id": None,
                "server_time": self.server_time,
                "stop_attached": True,
            }
        raise AdapterError("the terminal operation is unknown", code="malformed")
