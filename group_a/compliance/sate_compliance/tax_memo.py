"""Tax/reporting memo slot (**A-FEE-05**, Appendix D)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxReportingMemo:
    memo_id: str
    jurisdiction: str
    reporting_currency_rule: str
    professional_review_required: bool
    appendix_d_assumption_id: str = "APP-D-TAX-01"

    def slot_filled(self) -> bool:
        return bool(self.memo_id and self.reporting_currency_rule)
