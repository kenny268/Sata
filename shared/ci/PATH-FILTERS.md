# Path-filtered deploy

Workflows live in `.github/workflows/`. A push to `main` runs only the workflows whose `paths` match.

| Workflow | Paths | Artifact |
|----------|-------|----------|
| `deploy-group-a.yml` | `group_a/**` | `group-a-<sha>` |
| `deploy-group-b.yml` | `group_b/**` | `group-b-<sha>` |
| `deploy-shared.yml` | `shared/**` | `shared-<sha>` |

`ci-invariants.yml` runs on every pull request and on every push. It does not deploy. It checks that the trees do not import each other and that strategy does not depend on the credential crate.

Docs-only changes (`docs/**`) match none of the deploy workflows.

Phase 1 jobs build stubs. They do not contact a broker and they do not publish to a host.
