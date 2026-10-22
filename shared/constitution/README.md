# Constitution

Signed configuration for one group. Appendix A is the staging example. `tighten_lock_hours` and `loosen_lock_hours` are 0, the open A-DEC-04 placeholder. LIVE stays closed while those hours are unset, while `broker_balance_cap` is 0, or while the mode is SIM.

The verify key is pinned in `config/staging.json`. The private key is not in this repo. An artifact is Ed25519-signed over the canonical document. The kernel refuses a missing signature, a bad signature, a wrong key id, an expiry, or a version other than the pin.

The first version activates immediately and is the only active version. A later edit is a visible proposal. It does not activate on read. While the hours are still the placeholder, a trading edit cannot activate. Setting the hours is a proposal of its own, and the tighten value must be shorter than the loosen value. After that, a tightening edit waits the tighten hours and a loosening edit waits the loosen hours. Emergency activation accepts a signed tightening change only, and it records the caller's pre-mortem on the fact log. Loosening by that path is refused. A proposal records its change reason and stays visible. The kernel process requires the pinned version and refuses to start without it. A verdict input carries that constitution version and is refused when it does not match the loaded artifact.

`cost_allocation` is stored as written. This service does not split shared costs. There is no per-trade approval. A-DEC-01, A-DEC-02, A-DEC-04, and A-DEC-05 stay open.
