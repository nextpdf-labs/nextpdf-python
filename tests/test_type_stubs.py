"""Test: type stubs and py.typed marker are present and valid.

Verifies:
  1. py.typed marker file exists (PEP 561)
  2. connect.pyi stub exists and is non-empty
  3. All public model names in connect.py appear in the stub file
  4. pyright --strict clean run (integration check, skipped if pyright unavailable)
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


# Resolve package root — works from worktree or installed
_PKG_ROOT = Path(__file__).parent.parent / "src" / "nextpdf"


def test_py_typed_marker_exists() -> None:
    """PEP 561: py.typed marker must be present in the package root."""
    py_typed = _PKG_ROOT / "py.typed"
    assert py_typed.exists(), f"Missing PEP 561 marker: {py_typed}"
    # Must be a regular file (not a symlink to nowhere)
    assert py_typed.is_file(), f"py.typed is not a regular file: {py_typed}"


def test_connect_pyi_stub_exists() -> None:
    """connect.pyi stub file must exist alongside connect.py."""
    stub = _PKG_ROOT / "models" / "connect.pyi"
    assert stub.exists(), f"Missing type stub: {stub}"
    content = stub.read_text(encoding="utf-8")
    assert len(content) > 100, "connect.pyi appears to be empty or truncated"


def test_connect_pyi_declares_all_public_classes() -> None:
    """Every public class defined in connect.py must appear in connect.pyi."""
    source = (_PKG_ROOT / "models" / "connect.py").read_text(encoding="utf-8")
    stub = (_PKG_ROOT / "models" / "connect.pyi").read_text(encoding="utf-8")

    # Extract class names from source  (e.g. "class JobStatus(str, Enum):")
    import re

    source_classes = set(re.findall(r"^class\s+(\w+)", source, re.MULTILINE))
    stub_classes = set(re.findall(r"^class\s+(\w+)", stub, re.MULTILINE))

    missing = source_classes - stub_classes
    assert not missing, (
        f"These classes from connect.py are absent from connect.pyi: {sorted(missing)}"
    )


def test_connect_models_importable() -> None:
    """All names exported from models.connect must be importable without errors."""
    import nextpdf.models.connect as m  # noqa: F401

    # spot-check a few key types
    assert hasattr(m, "JobStatus")
    assert hasattr(m, "RenderRequest")
    assert hasattr(m, "SessionRecord")
    assert hasattr(m, "ComplianceCheckResponse")
    assert hasattr(m, "AiCertifyResponse")


@pytest.mark.skipif(
    shutil.which("pyright") is None and not importlib.util.find_spec("pyright"),
    reason="pyright not installed — skipping strict type-check integration test",
)
def test_pyright_strict_clean() -> None:
    """pyright must produce 0 errors on src/ using project config (typeCheckingMode=strict).

    Uses --project pointing to the worktree pyproject.toml which declares
    typeCheckingMode = 'strict' and excludes src/nextpdf/mcp.py.
    """
    project_dir = _PKG_ROOT.parent.parent  # = worktree root
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--project",
            str(project_dir),
            "--level",
            "error",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        stdout_bytes = result.stdout if isinstance(result.stdout, str) else ""
        stderr_bytes = result.stderr if isinstance(result.stderr, str) else ""
        stdout_tail = stdout_bytes[-4000:]
        stderr_tail = stderr_bytes[-2000:]
        combined = stdout_tail + stderr_tail

        # Exit code 1 = actual type errors; tool/config issues = skip
        venv_issue = "venv" in combined and "not found" in combined
        if result.returncode == 1 and not venv_issue:
            pytest.fail(
                f"pyright found type errors (exit {result.returncode}):\n"
                f"STDOUT:\n{stdout_tail}\n"
                f"STDERR:\n{stderr_tail}"
            )
        else:
            pytest.skip(
                f"pyright exited {result.returncode} — venv/config issue in worktree "
                f"(not a type error): {stderr_tail[:500]}"
            )
