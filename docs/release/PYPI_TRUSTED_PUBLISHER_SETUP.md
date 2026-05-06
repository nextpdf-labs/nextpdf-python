# PyPI Trusted Publisher Setup (OIDC)

> Operational runbook for registering the `nextpdf-labs/nextpdf-python` GitHub
> repository as an OIDC trusted publisher on PyPI.
>
> **Symptom this fixes**: `Trusted publishing exchange failure: invalid-publisher`
> on `Publish` workflow tag pushes (e.g. the `v1.0.0` tag failure on 2026-04-01).
>
> The repo, workflow file, and environment are correctly configured (see the
> matching items in `PYPI_PUBLISH_CHECKLIST.md`). The missing step is the
> **PyPI side registration** — without it, PyPI rejects the OIDC token even
> though GitHub mints it correctly.

---

## What is a trusted publisher?

PyPI's trusted-publisher feature lets a GitHub Actions workflow upload to
PyPI without a long-lived API token. Instead, GitHub mints a short-lived
OIDC token whose claims (repo, workflow, environment, ref) PyPI checks
against an allow-list registered on the PyPI account.

If the OIDC claims do not match a registered publisher exactly, PyPI rejects
the upload with `invalid-publisher` and the publish fails.

---

## Required claim values

These values MUST match between the GitHub Actions workflow and the PyPI
trusted-publisher entry, exactly:

| OIDC claim          | Required value                  | Source in this repo                                  |
|---------------------|---------------------------------|------------------------------------------------------|
| Repository owner    | `nextpdf-labs`                  | GitHub org                                           |
| Repository          | `nextpdf-python`                | GitHub repo name                                     |
| Workflow filename   | `publish.yml`                   | `.github/workflows/publish.yml`                      |
| Environment         | `pypi`                          | `environment: pypi` in `publish.yml`                 |
| Ref (optional)      | `refs/tags/v*` (recommended)    | Tag prefix used for releases                         |

---

## One-time setup

### Step 1 — Create the PyPI project (if not already published)

If `nextpdf` does not yet exist on PyPI, the trusted-publisher entry is
registered as a **pending publisher** (PyPI registration page) before the
first publish. After the first successful publish, it converts to a regular
trusted publisher.

If `nextpdf` already exists on PyPI from a manual upload, skip to Step 2.

### Step 2 — Add the trusted publisher on PyPI

1. Sign in at https://pypi.org/account/login/.
2. Navigate to the project at https://pypi.org/manage/project/nextpdf/.
3. Open the **Publishing** tab (left sidebar).
4. Under **Add a new pending / trusted publisher**, choose **GitHub**.
5. Fill in the form **exactly**:

   | Field                     | Value                  |
   |---------------------------|------------------------|
   | PyPI Project Name         | `nextpdf`              |
   | Owner                     | `nextpdf-labs`         |
   | Repository name           | `nextpdf-python`       |
   | Workflow filename         | `publish.yml`          |
   | Environment name          | `pypi`                 |

6. Click **Add**.

### Step 3 — Pre-flight test

Trigger a dry-run by pushing an annotated tag in a sandbox repo, OR — if
already at the next release — push the next real tag. The workflow should:

1. Trigger `Publish` on the tag.
2. `pypa/gh-action-pypi-publish@release/v1` requests an OIDC token from
   GitHub (`ACTIONS_ID_TOKEN_REQUEST_URL` + `ACTIONS_ID_TOKEN_REQUEST_TOKEN`
   are present because the job has `permissions: id-token: write`).
3. PyPI's OIDC endpoint accepts the token (claims match the registered
   publisher).
4. The package is uploaded.

If Step 3 still fails with `invalid-publisher`, double-check **every claim**
in the table above for typo / case mismatch / trailing whitespace. PyPI is
strict — `Publish.yml` ≠ `publish.yml`.

---

## Common failure modes

| Failure                              | Diagnosis                                                                 |
|--------------------------------------|---------------------------------------------------------------------------|
| `invalid-publisher`                  | One of the claims doesn't match the registered publisher entry.           |
| `valid-token-no-corresponding-publisher` | No publisher entry registered yet (Step 2 not done).                  |
| `permission denied` on token mint    | `permissions: id-token: write` missing from the publish job.              |
| `not-a-pypi-trusted-publisher`       | Repo is private *and* trusted-publisher beta access not enabled for org.  |

---

## Standards anchor

- NIST SP 800-218 SSDF PS.2 — verify release integrity. OIDC trusted
  publishing replaces long-lived secrets with short-lived attestable tokens.
- NIST SP 800-204D §C.4.5 — software-supply-chain attestation.
- The Update Framework (TUF) §5.6 — keyless signing via federated identity.

---

## Cross-references

- `PYPI_PUBLISH_CHECKLIST.md` — the broader release checklist (this doc fills
  in the OIDC setup step that was previously a checkbox without a runbook).
- `RELEASE_RUNBOOK.md` §4 — references trusted-publisher use.
- `ROLLBACK_AND_HOTFIX_PLAN.md` §2 — references OIDC verification on rollback.
