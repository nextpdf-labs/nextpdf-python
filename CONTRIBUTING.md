# Contributing to nextpdf

Thank you for considering a contribution. This document covers the development workflow.

## Development Setup

Clone the repository and install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/nextpdf-labs/nextpdf-python.git
cd nextpdf-python
uv sync --dev
```

This creates a virtualenv in `.venv/` and installs all dev dependencies.

To also install the MCP optional extra:

```bash
uv sync --dev --extra mcp
```

## Code Style

The project enforces strict typing and linting:

- **ruff** for linting and formatting (`ruff check`, `ruff format`)
- **mypy --strict** for static type checking
- **pyright strict** as a secondary type checker

Run all checks:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pyright src/
```

Key rules:
- All functions must have type annotations (parameters and return types)
- Use `from __future__ import annotations` in every module
- Prefer `final` classes and `readonly` properties where appropriate
- No `Any` without a documented reason

## Testing

Tests use pytest with pytest-asyncio:

```bash
uv run pytest
```

Run a specific test file:

```bash
uv run pytest tests/test_cli.py -v
```

All tests must pass before submitting a PR. The test suite currently has 119 tests covering the client, async client, CLI, backends, and models.

## Pull Request Process

1. Fork the repo and create a feature branch from `main`.
2. Make your changes. Add tests for new functionality.
3. Ensure all checks pass: `ruff check`, `mypy --strict`, `pytest`.
4. Write a clear PR description explaining what changed and why.
5. Keep PRs focused -- one logical change per PR.

### Commit Messages

Use clear, descriptive commit messages. Prefer imperative mood ("Add table extraction" not "Added table extraction").

## License

This project is MIT licensed. By submitting a contribution, you agree that your contribution is licensed under the same MIT license.
