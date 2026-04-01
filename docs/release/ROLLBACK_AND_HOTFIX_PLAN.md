# Rollback and Hotfix Plan -- nextpdf-python 1.0.0

Operational contingency plan for the 1.0.0 GA release.

---

## 1. PyPI Publish Failure

### CI Publish Workflow Fails

1. Check the GitHub Actions run log for the failing step.
2. Verify the OIDC trusted publisher configuration in PyPI matches the repository, workflow file name, and environment name exactly.
3. Verify the git tag format matches the `v*` pattern expected by the workflow trigger.
4. Re-run the workflow from the Actions tab once the issue is resolved.

### twine / Upload Fails

If CI cannot be fixed quickly, publish manually:

```bash
uv build
twine upload dist/*
```

Use a PyPI API token scoped to the `nextpdf` project. Do not use username/password authentication.

### Package Metadata Rejected by PyPI

1. Fix the offending field in `pyproject.toml`.
2. Delete the local and remote tag:
   ```bash
   git tag -d v1.0.0
   git push origin :refs/tags/v1.0.0
   ```
3. Commit the metadata fix.
4. Re-tag and push:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
5. CI will trigger the publish workflow automatically.

---

## 2. Critical Bug After Publication

### Hotfix Criteria (warrants 1.0.1 release)

- Test failure on any supported Python version (3.10, 3.11, 3.12, 3.13).
- Import error on a clean install (`pip install nextpdf` fails to import).
- CLI crash on valid input.
- Security vulnerability in a dependency or in nextpdf code.

### Documentation-Only Fix Criteria (no release needed)

- README inaccuracy that does not affect runtime behavior.
- Example code that does not match the actual API.
- Misleading help text in CLI `--help` output.

For documentation-only fixes, commit directly to `main`. No tag or release required.

### Hotfix Process

1. Fix the issue on `main`.
2. Bump version to `1.0.1` in `pyproject.toml`.
3. Tag and push:
   ```bash
   git tag v1.0.1
   git push origin main --tags
   ```
4. CI auto-publishes to PyPI on tag push.

### PyPI Yanking Policy

- Only yank `1.0.0` if it causes **data loss** or contains a **security vulnerability**.
- In all other cases, prefer publishing `1.0.1` over yanking.
- Yanking is irreversible in practice (the version number cannot be reused).

---

## 3. MCP Dependency or Startup Failure

### `mcp` Package Has Breaking Changes

Pin to the last known-good version in `pyproject.toml` optional dependencies:

```toml
[project.optional-dependencies]
mcp = ["mcp>=1.0,<1.1"]  # pin to known-good range
```

Release as `1.0.1` if this affects users who installed with `pip install nextpdf[mcp]`.

### MCP Server Fails to Start

Debugging order:

1. Verify the import guard: `mcp` must be importable before server initialization runs.
2. Check server initialization for unhandled exceptions at startup.
3. Verify tool registration decorators are applied correctly.

### Scope Boundary

MCP issues are **non-blocking** for core SDK functionality. The MCP integration is an optional extra. Core extraction, AST, and CLI features must remain unaffected by any MCP failure.

---

## 4. README Claim Challenged

### Local Backend Capability Claim

If a claim about local backend capability is challenged:

1. Review the specific claim against actual implementation.
2. Update README to be more explicit about beta limitations.
3. Ensure the Limitations section accurately reflects current state.

### Citation Accuracy Questioned

1. Point the reporter to the Limitations section.
2. Do not promise more than what is implemented and tested.
3. If the Limitations section is insufficient, expand it.

### Response Time

Documentation fixes must be committed within **24 hours** of a credible report.

---

## 5. Local Backend Beta Causes Confusion

### Users Expect Local Mode to Match Remote Quality

- Add a FAQ entry to the documentation explaining the difference between local and remote backends.
- Clarify that the local backend is a beta feature for offline and sandbox use cases.
- The remote backend (NextPDF Connect) is the recommended path for production accuracy.

### Users Want Local-First as Default

- Document clearly that the remote backend is recommended for production workloads.
- Local mode is designed for offline, air-gapped, and development/sandbox environments.
- Do not change the default backend without meeting the promotion criteria defined in the post-GA backlog.

### Startup Warning

Consider adding a log-level warning when `LocalBackend` is instantiated:

```
Local backend is in beta. For production accuracy, use the remote backend.
```

This warning should be visible at the default log level but suppressible via standard logging configuration.
