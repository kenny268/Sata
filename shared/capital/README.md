# Capital ledger

Five-state projection for one group scope. Equity, realised PnL, settled cash, reserved cash, and withdrawable cash are separate fields. Withdrawable is `settled - reserved - withdrawal hold - cash floor - pending obligations`, and never below zero. It is not copied from equity.

Broker snapshots come from the broker adapter (`kernel-a`) and must move forward in broker time. Manual adjustments come from the admin writer (`control-api`) and name one bucket. Both are appended to the fact log, then replayed. A saved projection that does not match that replay is rejected. A snapshot cannot set the ratified base. The first `bind_rcb` event sets that base. A later bind cannot move it. A withdrawal reduces it immediately and records the broker fee and the FX cost as separate figures. A deposit is stored as inert: it does not raise the base, including when the group is halted. The mock broker posts the deposit and the following snapshot together. Replaying an `rcb_change` copies the RCB service base onto this projection. The cool-off and the passkey live in that service.

Fill events require commission, swap, slippage, and an FX rate. A swap accrual is its own event, and zero is accepted only when the caller sends that zero. An obligation funded by another scope is flagged as a cross-broker owner transfer and is not added to this group's cash.

Staging config: `config/staging.json`. The projection database under `var/` is gitignored and is rebuilt from the log on boot.
