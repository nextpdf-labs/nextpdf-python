# PyPI Publish Checklist -- nextpdf 1.0.0

Complete every item before and after publishing to PyPI.

---

## Package Metadata Verification

Cross-reference against `pyproject.toml`:

- [ ] `name = "nextpdf"`
- [ ] `version = "1.0.0"`
- [ ] `description = "Citation-ready PDF extraction for Python - AI-agent-native"` -- no overclaims
- [ ] `license = { text = "MIT" }`
- [ ] `requires-python = ">=3.10"`
- [ ] Classifier: `"Development Status :: 5 - Production/Stable"`
- [ ] Classifier: `"Typing :: Typed"`
- [ ] `[project.scripts]` has `nextpdf = "nextpdf.cli:main"`
- [ ] `[project.urls]` contains Homepage, Documentation, Repository, Changelog, Issues
- [ ] `keywords` includes: pdf, ai, llm, mcp, document-intelligence
- [ ] `dependencies` lists: httpx>=0.27, pydantic>=2.0, anyio>=4.0, click>=8.0, pypdf>=4.0
- [ ] `[project.optional-dependencies]` has `mcp = ["mcp>=1.0,<2.0"]`

---

## Build Verification

Run locally before relying on CI:

```bash
rm -rf dist/
uv build
```

### Wheel checks

- [ ] `uv build` produces `dist/nextpdf-1.0.0-py3-none-any.whl`
- [ ] `uv build` produces `dist/nextpdf-1.0.0.tar.gz`
- [ ] `twine check dist/*` passes with no errors or warnings

### Wheel content inspection

```bash
unzip -l dist/nextpdf-1.0.0-py3-none-any.whl
```

- [ ] Wheel contains `py.typed` marker file
- [ ] Wheel contains all source modules (19 `.py` files under `nextpdf/`)
- [ ] Wheel contains `METADATA` with correct version and description
- [ ] No `.env`, credentials, `.git`, or dev-only files in the distribution
- [ ] No `tests/` directory in the wheel
- [ ] Build backend is hatchling (declared in `[build-system]`)

### Sdist content inspection

```bash
tar tzf dist/nextpdf-1.0.0.tar.gz | head -30
```

- [ ] Contains `pyproject.toml`
- [ ] Contains `README.md`
- [ ] Contains `LICENSE` (or license is inline in pyproject.toml)
- [ ] Contains `src/nextpdf/` source tree

---

## PyPI Configuration

### Trusted publisher (OIDC)

- [ ] Trusted publisher configured in PyPI project settings for the GitHub repository `nextpdf-labs/nextpdf-python`
- [ ] Trusted publisher workflow is set to `publish.yml`
- [ ] Trusted publisher environment is set to `pypi`

### GitHub Actions workflow (`publish.yml`)

- [ ] Triggers on `push: tags: ["v*"]`
- [ ] Job runs on `ubuntu-latest`
- [ ] Job has `environment: pypi`
- [ ] Job has `permissions: id-token: write`
- [ ] Uses `astral-sh/setup-uv@v4` with `python-version: "3.12"`
- [ ] Builds with `uv build`
- [ ] Publishes with `pypa/gh-action-pypi-publish@release/v1`
- [ ] No manual token or password in the workflow (OIDC only)

---

## Post-Publish Verification

Run from a clean environment (not the development virtualenv):

```bash
python -m venv /tmp/nextpdf-pypi-check
source /tmp/nextpdf-pypi-check/bin/activate
```

### Install verification

- [ ] `pip install nextpdf==1.0.0` succeeds
- [ ] `pip install nextpdf` resolves to 1.0.0 (latest)
- [ ] `pip install nextpdf[mcp]==1.0.0` installs MCP dependency

### Runtime verification

- [ ] `nextpdf version` outputs `nextpdf 1.0.0`
- [ ] `nextpdf --help` prints usage without errors
- [ ] `python -m nextpdf version` works
- [ ] `python -c "from nextpdf import NextPDF; print('OK')"` prints OK

### PyPI page verification

Open `https://pypi.org/project/nextpdf/1.0.0/`:

- [ ] Project page renders README correctly (no broken markdown)
- [ ] Metadata sidebar shows correct license (MIT)
- [ ] Metadata sidebar shows correct Python version requirement (>=3.10)
- [ ] Classifiers display correctly
- [ ] Project URLs (Homepage, Docs, Repository, Changelog, Issues) are clickable and correct
- [ ] Release history shows 1.0.0 as the latest version
