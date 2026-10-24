"""Compose smoke: CRITICAL alert on simulated kernel stall."""

from sate_monitoring.alerts import AlertRouter
from sate_monitoring.heartbeat import HeartbeatMonitor
from sate_monitoring.on_call import OnCallRouter
from sate_monitoring.tg_wire import to_health_payload


def main() -> None:
    router = AlertRouter()
    on_call = OnCallRouter()
    monitor = HeartbeatMonitor(stall_threshold_sec=5.0, alert_budget_sec=60.0)
    monitor.beat(now=0.0)
    result = monitor.evaluate(now=10.0, router=router)
    if not result.detected or not result.alert_fired:
        raise SystemExit("expected CRITICAL on kernel stall")
    if router.delivered[0].severity != "CRITICAL":
        raise SystemExit("CRITICAL must not be suppressed")
    alert = router.delivered[0]
    on_call.dispatch(alert, muted=True)
    payload = to_health_payload(alert)
    if payload["severity"] != "CRITICAL":
        raise SystemExit("TG-PO-15 wire expected CRITICAL")
    print("monitoring ok")


if __name__ == "__main__":
    main()
