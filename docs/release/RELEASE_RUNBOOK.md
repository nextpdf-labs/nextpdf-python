# Release Runbook -- nextpdf 1.0.0

This is the step-by-step execution guide for releasing nextpdf 1.0.0 to PyPI.

---

## Pre-Release Checklist

- [ ] `version = "1.0.0"` in `pyproject.toml`
- [ ] `__version__ = "1.0.0"` in `src/nextpdf/_version.py`
- [ ] CHANGELOG.md contains a `[1.0.0]` section with the correct date
- [ ] All CI quality gates pass on main (pytest, mypy --strict, ruff check, ruff format --check, pyright)
- [ ] `uv build` produces `nextpdf-1.0.0-py3-none-any.whl` and `nextpdf-1.0.0.tar.gz`
- [ ] `twine check dist/*` passes with no warnings
- [ ] README reflects S2 positioning (no S1 overclaims about local backend accuracy)
- [ ] External review approved

---

## Release Execution Steps

### 1. Verify main branch is clean

```bash
git checkout main
git pull origin main
git status
```

There must be no uncommitted changes.

### 2. Run full quality gate locally

```bash
uv sync --dev
uv run mypy src --strict
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src
uv run pytest tests/ -v
```

All must pass with zero errors.

### 3. Verify build artifacts

```bash
rm -rf dist/
uv build
twine check dist/*
```

Expected output:
- `dist/nextpdf-1.0.0-py3-none-any.whl`
- `dist/nextpdf-1.0.0.tar.gz`
- twine reports PASSED for both files

### 4. Verify wheel contents

```bash
unzip -l dist/nextpdf-1.0.0-py3-none-any.whl | grep -E '\.py$|py\.typed'
```

Confirm:
- `py.typed` marker is present
- All 19 source `.py` files are included
- No dev files, `.env`, or credentials are present

### 5. Create release commit

```bash
git add -A
git commit -m "release: v1.0.0"
```

Only create this commit if there are pending changes (version bumps, changelog updates). If everything is already committed, skip to step 6.

### 6. Create annotated tag

```bash
git tag -a v1.0.0 -m "nextpdf 1.0.0 - GA release (S2)"
```

### 7. Push commit and tag

```bash
git push origin main
git push origin v1.0.0
```

### 8. Monitor CI publish pipeline

The `publish.yml` workflow triggers automatically on `v*` tag push. It will:

1. Check out the tagged commit
2. Set up Python 3.12 via `astral-sh/setup-uv@v4`
3. Build wheel and sdist via `uv build`
4. Publish to PyPI via `pypa/gh-action-pypi-publish@release/v1` using OIDC trusted publisher

Monitor the workflow run at:
```
https://github.com/nextpdf-labs/nextpdf-python/actions/workflows/publish.yml
```

Wait for the workflow to complete successfully before proceeding.

### 9. Create GitHub Release

Go to `https://github.com/nextpdf-labs/nextpdf-python/releases/new` or use the CLI:

```bash
gh release create v1.0.0 \
  --title "nextpdf 1.0.0" \
  --notes-file docs/release/GITHUB_RELEASE_NOTES_v1.0.0.md
```

Attach no extra assets -- the wheel and sdist are on PyPI.

---

## Post-Publish Verification

Run these checks from a clean virtual environment (not the development environment):

```bash
python -m venv /tmp/nextpdf-verify
source /tmp/nextpdf-verify/bin/activate
```

### Verify base install

```bash
pip install nextpdf==1.0.0
nextpdf version
```

Expected: `nextpdf 1.0.0`

### Verify MCP extra

```bash
pip install nextpdf[mcp]==1.0.0
python -c "import nextpdf; print(nextpdf.__version__)"
```

Expected: `1.0.0`

### Verify module runner

```bash
python -m nextpdf version
```

Expected: `nextpdf 1.0.0`

### Verify CLI commands exist

```bash
nextpdf --help
nextpdf extract --help
nextpdf ast --help
nextpdf info --help
```

All must print help text without errors.

### Verify PyPI page

Open `https://pypi.org/project/nextpdf/1.0.0/` and confirm:
- [ ] README renders correctly
- [ ] Metadata (license, classifiers, URLs) is correct
- [ ] Dependencies are listed accurately

### Post-Publish Checklist

- [ ] `pip install nextpdf` installs 1.0.0 (latest)
- [ ] `nextpdf version` outputs `nextpdf 1.0.0`
- [ ] `pip install nextpdf[mcp]` installs MCP dependencies
- [ ] `python -m nextpdf version` works
- [ ] PyPI page renders README correctly
- [ ] GitHub Release is published with release notes

---

## Rollback Procedure

If a critical defect is discovered after publish:

### Option A: Yank the release (PyPI stays, install blocked)

```bash
pip install twine
# Yank prevents new installs but keeps existing ones working
# Must be done via PyPI web UI: https://pypi.org/manage/project/nextpdf/release/1.0.0/
```

### Option B: Publish a patch release

1. Fix the defect on main
2. Bump version to `1.0.1`
3. Follow this runbook from step 2 onward with version `1.0.1`

Do not delete PyPI releases. Use yank for blocking installs, or publish a patch.
