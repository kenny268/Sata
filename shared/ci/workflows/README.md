# Workflows GitHub runs

GitHub Actions loads `.github/workflows/`. This folder records that those files are the Phase 1 pipelines:

| File | Role |
|------|------|
| [deploy-group-a.yml](../../../.github/workflows/deploy-group-a.yml) | Build, lint, test, dependency scan, and sha-named artifact for `group_a/**` |
| [deploy-group-b.yml](../../../.github/workflows/deploy-group-b.yml) | Placeholder check and sha-named artifact for `group_b/**` |
| [deploy-shared.yml](../../../.github/workflows/deploy-shared.yml) | Lint, test, and sha-named artifact for `shared/**` |
| [ci-invariants.yml](../../../.github/workflows/ci-invariants.yml) | Repo invariants on every push. Does not deploy. |

Path rules: [../PATH-FILTERS.md](../PATH-FILTERS.md).
