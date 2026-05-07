"""Test: pyproject.toml SBOM tooling configuration and generated output.

RAG anchor: cyclonedx_1_7_json_reference#x1.x65.x8.p24
  — component version MUST comply with semantic versioning (not enforced, but checked).

Verifies:
  1. [tool.cyclonedx] section is present in pyproject.toml
  2. schema_version = "1.7" declared
  3. output_file_pattern includes {version} placeholder
  4. SBOM generation CLI produces a valid CDX 1.7 JSON file (integration, skipped if
     cyclonedx-bom not installed)
  5. Generated SBOM contains required CISA minimum elements:
     - serialNumber / metadata / components / specVersion = "1.7"
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomllib  # type: ignore[no-reattr]  # fallback: pip install tomli


_REPO_ROOT = Path(__file__).parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"


def _load_pyproject() -> dict:  # type: ignore[type-arg]
    """Load pyproject.toml using tomllib (stdlib 3.11) or tomli fallback."""
    try:
        import tomllib as tl
    except ImportError:
        try:
            import tomli as tl  # type: ignore[no-reattr]
        except ImportError:
            pytest.skip("tomllib / tomli not available — skipping pyproject parse tests")
            return {}  # unreachable but satisfies type checker

    with _PYPROJECT.open("rb") as fh:
        return tl.load(fh)


def test_pyproject_cyclonedx_section_present() -> None:
    """[tool.cyclonedx] section must exist in pyproject.toml."""
    config = _load_pyproject()
    tool = config.get("tool", {})
    assert "cyclonedx" in tool, (
        "Missing [tool.cyclonedx] section in pyproject.toml. "
        "Add it per Cycle 5 D5 SBOM requirement."
    )


def test_pyproject_cyclonedx_schema_version_1_7() -> None:
    """[tool.cyclonedx].schema_version must be '1.7'."""
    config = _load_pyproject()
    cdx = config.get("tool", {}).get("cyclonedx", {})
    assert cdx.get("schema_version") == "1.7", (
        f"Expected schema_version='1.7', got {cdx.get('schema_version')!r}"
    )


def test_pyproject_cyclonedx_output_pattern_has_version() -> None:
    """output_file_pattern must contain {version} for per-release naming."""
    config = _load_pyproject()
    cdx = config.get("tool", {}).get("cyclonedx", {})
    pattern = cdx.get("output_file_pattern", "")
    assert "{version}" in pattern, (
        f"output_file_pattern must contain {{version}}, got: {pattern!r}"
    )
    assert pattern.endswith(".cdx.json"), (
        f"output_file_pattern must end in .cdx.json (C1 alignment), got: {pattern!r}"
    )


def test_project_version_semver() -> None:
    """project.version must be a valid SemVer string (CDX component version compliance)."""
    config = _load_pyproject()
    version = config.get("project", {}).get("version", "")
    # Simple SemVer pattern: MAJOR.MINOR.PATCH (pre/build tags optional)
    assert re.match(r"^\d+\.\d+\.\d+", version), (
        f"project.version '{version}' does not match SemVer pattern X.Y.Z"
    )


@pytest.mark.skipif(
    shutil.which("cyclonedx-py") is None and shutil.which("cyclonedx_py") is None,
    reason="cyclonedx-bom not installed — skipping SBOM generation integration test",
)
def test_sbom_generation_produces_valid_cdx17() -> None:
    """cyclonedx-py must generate a schema-valid CDX 1.7 JSON SBOM."""
    config = _load_pyproject()
    version = config.get("project", {}).get("version", "0.0.0")
    output_path = _REPO_ROOT / f"sbom-{version}.cdx.json"

    # Use cyclonedx-py environment command (inspects installed packages)
    exe = shutil.which("cyclonedx-py") or shutil.which("cyclonedx_py") or "cyclonedx-py"
    result = subprocess.run(
        [
            exe,
            "environment",
            "--output-format",
            "JSON",
            "--schema-version",
            "1.7",
            "--outfile",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(
            f"cyclonedx-py failed (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout[-2000:]}\n"
            f"STDERR: {result.stderr[-2000:]}"
        )

    assert output_path.exists(), f"SBOM output file not created: {output_path}"

    # Parse and validate required CDX 1.7 top-level fields
    bom: dict = json.loads(output_path.read_text(encoding="utf-8"))  # type: ignore[type-arg]

    assert bom.get("specVersion") == "1.7", (
        f"specVersion must be '1.7', got {bom.get('specVersion')!r}"
    )
    assert "serialNumber" in bom, "CDX SBOM missing required 'serialNumber' field"
    assert "metadata" in bom, "CDX SBOM missing required 'metadata' field"
    assert "components" in bom, "CDX SBOM missing required 'components' field"
    assert isinstance(bom["components"], list), "'components' must be a list"

    # CISA minimum element: at least one component with name + version
    assert len(bom["components"]) > 0, "SBOM must contain at least one component"
    first = bom["components"][0]
    assert "name" in first, "Component missing 'name' field"
    assert "version" in first, "Component missing 'version' field (CISA minimum element)"
