"""§15 scenario catalog (**OPS**)."""

from __future__ import annotations

SCENARIO_FAMILIES: dict[str, tuple[str, ...]] = {
    "TS": (
        "TS-01",
        "TS-02",
        "TS-03",
        "TS-04",
        "TS-05",
        "TS-06",
        "TS-07",
        "TS-08",
        "TS-09",
        "TS-10",
        "TS-11",
        "TS-12",
        "TS-13",
    ),
    "HL": ("HL-01", "HL-02", "HL-07", "HL-08", "HL-A", "HL-B", "HL-C", "HL-D", "HL-E", "HL-F"),
    "OC": ("OC-01", "OC-02", "OC-03", "OC-04", "OC-05", "OC-06", "OC-07", "OC-08"),
    "AM": ("AM-01", "AM-02", "AM-03", "AM-A5"),
    "CT": ("CT-01", "CT-08"),
    "BF": ("BF-01", "BF-02", "BF-03", "BF-04", "BF-05", "BF-06", "BF-07"),
    "MP": ("MP-01", "MP-02", "MP-03"),
}


def all_scenario_ids() -> list[str]:
    items: list[str] = []
    for family in SCENARIO_FAMILIES.values():
        items.extend(family)
    return items
