# Control API

**Phase 17** router (`ControlApi`) plus stdlib HTTP (`sate_control.http_server`): CSRF on control POSTs, rate limiting, WebAuthn assertion shape checks, and optional RCB ratify wiring. Compose runs `python -m sate_control.bootstrap`; dev HTTP via `python -m sate_control.http_server` (port **8080**).
