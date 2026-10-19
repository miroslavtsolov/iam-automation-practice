# IAM Automation Practice Project

A small end-to-end IAM access-review automation tool built to practice and demonstrate core enterprise identity automation concepts: OAuth 2.0 client-credentials authentication, API pagination, cross-source reconciliation, audit logging, and safe remediation.

The tool authenticates against a local Keycloak instance, retrieves the user population via the Admin REST API, cross-references it against a mock HR feed, flags discrepancies, and generates a formatted Excel access-review report, with every action logged.

Built and tested hands-on in a local environment, using Claude AI to assist with script generation and troubleshooting research.

## Architecture

```
                     ┌──────────────────────┐
                     │   Keycloak (Docker)  │
                     │  OAuth2 / Admin REST │
                     └──────────┬───────────┘
                                │ client_credentials grant
                                │ (auth.py)
                                ▼
                     ┌──────────────────────┐
                     │   fetch_users.py     │◄── paginated GET /users
                     │  (+ disable_user)    │◄── PUT /users/{id} (remediation)
                     └──────────┬───────────┘
                                │ list[dict] of Keycloak users
                                ▼
   hr_feed.csv ──────► ┌───────────────────────┐
   (mock HR source)    │    reconcile.py       │  pandas merge on email
                       │    orphaned /         │ 
                       │    terminated-enabled │
                       └────────────┬──────────┘
                                │
                 ┌──────────────┼───────────────┐
                 ▼                              ▼
       ┌──────────────────┐          ┌───────────────────────┐
       │    report.py     │          │    remediate.py       │
       │  → .xlsx report  │          │  --dry-run / --confirm│
       │(highlighted rows)│          │  disables flagged     │
       └──────────────────┘          │  accounts             │
                                     └───────────────────────┘

                     logger.py → iam_review.log
             
```

# Every stage writes to a single shared log file in a continuous audit trail.


## Scripts and functions

| File | Function | Purpose |
|---|---|---|
| `auth.py` | `get_access_token()` | Exchanges the client ID/secret for a bearer token via Keycloak's OIDC token endpoint (OAuth 2.0 client-credentials grant). |
| `fetch_users.py` | `fetch_all_users()` | Calls the Keycloak Admin REST API (`GET /admin/realms/{realm}/users`), paginating in batches of 20 until no users remain. |
| `fetch_users.py` | `disable_user(user_id)` | Calls `PUT /admin/realms/{realm}/users/{id}` to set `enabled: false` on a specific Keycloak user, identified by their internal UUID. |
| `logger.py` | `get_logger()` | Configures a shared logger that writes timestamped INFO/WARNING lines to `iam_review.log`, used by every other script instead of `print()`. |
| `reconcile.py` | `reconcile()` | Pulls Keycloak users, loads `hr_feed.csv`, left-joins on email, and returns three DataFrames: the full merged table, orphaned accounts (in Keycloak but not HR), and terminated-but-enabled accounts (HR says terminated, Keycloak still shows enabled). Accounts with no email (e.g. service accounts) can't be correlated, so they are skipped and logged for manual review. |
| `report.py` | `build_report()` | Runs `reconcile()` and writes `access_review_report.xlsx` — a bold-headered sheet with orphaned and terminated-but-enabled rows highlighted red. |
| `remediate.py` | `remediate(dry_run=True)` | Runs `reconcile()`, combines orphaned + terminated-but-enabled rows, and either logs what it *would* disable (`--dry-run`) or actually calls `disable_user()` for each one (`--confirm`). Refuses to run live without an explicit `--confirm` flag, even if `--dry-run` is omitted. |
| `test_reconcile.py` | `test_reconcile_returns_dataframe`, `test_terminated_but_enabled_detection` | Pytest tests that mock `fetch_all_users()` so `reconcile()`'s logic can be verified without a live Keycloak/Docker instance running. |

https://www.keycloak.org/docs-api/latest/rest-api/index.html

---

## Setup

### 1. Prerequisites
- Ubuntu 22.04/24.04 VM (or equivalent Linux environment)
- Docker
- Python 3

### 2. Run Keycloak
```bash
docker run -d --name keycloak -p 8080:8080 --env-file keycloak.env -v keycloak_data:/opt/keycloak/data quay.io/keycloak/keycloak:latest start-dev
```

keycloak.env:

```
KEYCLOAK_ADMIN=
KEYCLOAK_ADMIN_PASSWORD=
```

### 3. Configure Keycloak
In the admin console (`http://localhost:8080`):
1. Create a realm (e.g. `iam-lab`).
2. Create a confidential OpenID Connect client (`iam-automation`) with
   **Client authentication: On** and **Service accounts roles** enabled.
3. Under the client's **Credentials** tab, copy the client secret.
4. Under **Service account roles**, assign `view-users` (and `manage-users`
   if remediation step will make real changes) from the
   `realm-management` client.
5. Create a few test users under **Users**.

### 4. Configure the project
```bash
git clone <repo-url>
cd iam-automation-practice
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # or: pip install requests pandas openpyxl python-dotenv PyJWT pytest
```

Create `.env`:
```
KEYCLOAK_BASE_URL=http://localhost:8080
REALM=iam-lab
CLIENT_ID=iam-automation
CLIENT_SECRET=<client secret>
```

Create/edit `hr_feed.csv` to deliberately mismatch some of Keycloak test users — that mismatch is what the reconciliation logic detects.

---

# Usage

Generate the access-review report -> ```python3 report.py```

Produces `access_review_report.xlsx` and appends to `iam_review.log`.

Preview what remediation would do, without changing anything -> ```python3 remediate.py --dry-run```

Actually disable flagged accounts (requires `manage-users` role) -> ```python3 remediate.py --confirm```

---

## Safety notes

- **Least privilege by default** — the service account only has `view-users`
  unless `manage-users` is deliberately added for remediation testing.
- **Dry-run by default, explicit confirmation for live changes** —
  `remediate.py` requires `--confirm` to make any real change; omitting both
  `--dry-run` and `--confirm` causes it to refuse and do nothing.
- **Secrets stay out of version control** — `.env`, logs, and the generated
  report are all in `.gitignore`.
- **Every action is logged** — `iam_review.log` provides a full audit trail
  of what ran, what was found, and what (if anything) was changed.
