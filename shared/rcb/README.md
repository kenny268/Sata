# RCB service

Ratified capital base for one group. An increase is a fact-log `rcb_change` and stays a proposal until 14 consecutive days have passed without an L2, L3, or L4 halt and the owner supplies a passkey assertion.

`POST /capital/ratify` is `post_capital_ratify`. The assertion is required and is not checked as WebAuthn until Phase 16. The service has no path that fills the assertion in itself. A refusal carries a reason code: `passkey_required`, `cool_off_incomplete`, `injections_paused`, or `nothing_to_ratify`.

A deposit or profit proposal does not move the base. While a halt is active, or while L2+ has paused injections, the deposit is recorded as `inert_halt`. L2, L3, and L4 restart the cool-off. L1 does not. With no ratification the existing base remains, and the limit is `min(ratified base, equity)`. The Group A reference floor is 500 and the Group B reference floor is 200; the floor test reads the ratified base.

A fact-log `halt` event at L2, L3, or L4 restarts that clock as well. The writer of the halt fact is the halt source. Another writer cannot append an `rcb_change`.

A withdrawal reduces the base immediately after the same group's capital projection shows enough withdrawable cash. Fee and FX stay separate fields. The capital projection copies this base when it replays an `rcb_change`. The kernel takes `rcb_version` and `effective_limit` from this projection. Version 0 is refused. Treasury will not authorise a reimbursement above the base.

The staging soak gate is unchanged. A-DEC-02 and A-DEC-05 stay open.
