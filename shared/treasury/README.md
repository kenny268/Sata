# Treasury

Reimbursement owed is a separate ledger from broker cash. An owner-paid invoice increases the owed balance and does not change withdrawable, settled cash, or the ratified base. The event is rejected if it carries those cash fields. A broker-deducted cost is tagged and does not create an owed balance. Eligibility for one group cannot be decided from another group's capital.

Every direct cost is tagged A or B. A shared cost is tagged GLOBAL and carries a basis, a rule version, evidence, and an explicit share for each group. Those shares are supplied by the caller. This service does not calculate a pro-rata split, because that basis is still an open decision.

A reimbursement moves through the recorded states one step at a time. Authorisation sets `notice_due` for a later Telegram notice and does not mark the case successful. Owner confirmation does not either. It becomes reimbursed only after broker reconciliation records a matched movement. A missed deadline keeps the owed amount. Eligibility that the group's own cash cannot cover, or that exceeds the ratified base, is deferred and stays pending. A saved dashboard that does not match the fact-log replay is rejected.

The read model is `dashboard`. It reports status, owed amount, and open obligations for one scope. The web app can consume it later. Recording an obligation stores the exposure-reduction flag and does not move broker cash.

Staging config: `config/staging.json`. The projection under `var/` is gitignored and is rebuilt from the fact log on boot.
