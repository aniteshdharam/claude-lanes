# Example CLAUDE.md sections for the lanes plugin

Copy what fits into your project's `CLAUDE.md`. Both sections are optional; the skill works
without them, with its default high-risk list and no gate map.

## High-risk paths

These add to the skill's default categories (schema and migrations; deleting or overwriting
stored data; money, units and rounding; auth, sessions, permissions, secrets, personal data;
what users are served; the tests' expected values; a public API; infrastructure, deploy and CI
config). A change under any of these paths is Lane H at any size.

- migrations/
- app/billing/
- app/auth/
- api/public/
- .github/workflows/
- infra/

## Gate map

| You changed... | Run | What it checks |
|---|---|---|
| migrations/ | `make migrate-check` | upgrade and downgrade on a scratch database |
| app/billing/ | `make test-money` | the money fixtures; the correctness gate for amounts |
| api/public/ | `make api-contract` | responses against the published schema |
| anything under app/ | `make test` | the unit suite |
| docs/ | **none** | no check watches it: a reader does |

The correctness gate for this repo is `make test-money` plus `make api-contract`.
