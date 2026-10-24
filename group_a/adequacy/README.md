# Group A SIM-adequacy & ops evidence (Phases 22–23)

| ID | Module |
|----|--------|
| **A-P1-01** | `build_adequacy_report()` — reproducible **A-SIM-01–08** from stored evidence |
| **A-P1-04** | Treasury `cost_allocation.shared_cost_payload()` (**A-DEC-05** `pro_rata_rcb`) |
| **A-P1-05** | `champion.compare_champion_challenger()` + frozen promotion params |
| **A-P1-07** | `dashboard.build_performance_panels()` net-of-cost |
| **A-PERF-01–02** | `perf.performance_snapshot()` TWR + bootstrap retirement |

**Blockers:** **A-SIM-04** final pass blocked while **A-DEC-03** is open (report status `blocked`).

**Scenarios:** `scenario_runner.run_scenario_suite()` — TS executable + HL/MP hooks + full §15 catalog for CI.

**One-click:** `runner` reads `SATE_ADEQUACY_FACTLOG_PATH` (fact extract), optional champion shadow JSON pair, writes `adequacy-report.json` + `performance-dashboard.json`, optional `SATE_ADEQUACY_PERSIST_FACTLOG`.

**Scenarios:** TS-01–04/09–10, HL-01, OC-01, AM-02/03, CT-08, BF-01, MP-01–03 executable; remainder catalogued stubs (suite export counts executable vs stub).

**Phase 23:** `sim_ops_wire` ( **`sim_runner`** sessions → fact log), `sim_ops_daily` rollup/drills, `rollup_from_log`, `phase23_log`, operator flag `SATE_SIM_WALL_CLOCK_ELAPSED`. Compose: `sim-ops-phase23`, `strategy-sim-runner`, `sim-ops-daily`.

Compose: `adequacy`. Nightly: `.github/workflows/scenario-suite.yml`.
