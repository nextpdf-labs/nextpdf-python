"""NextPDF CLI — command-line interface for PDF extraction."""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any

import click

from ._client import NextPDF
from ._version import __version__
from .models.errors import NextPDFError

logger = logging.getLogger("nextpdf.cli")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_pdf(source: str) -> bytes:
    """Read PDF bytes from a file path or stdin (when source is '-')."""
    if source == "-":
        data = sys.stdin.buffer.read()
        if not data:
            raise click.BadParameter("No data received on stdin.")
        return data
    path = Path(source)
    if not path.exists():
        raise click.BadParameter(f"File not found: {source}")
    if not path.is_file():
        raise click.BadParameter(f"Not a file: {source}")
    return path.read_bytes()


def _build_client(base_url: str, api_key: str) -> NextPDF:
    """Construct a NextPDF sync client."""
    return NextPDF(base_url=base_url, api_key=api_key)


def _write_output(content: str, output: str | None) -> None:
    """Write content to a file or stdout."""
    if output:
        Path(output).write_text(content, encoding="utf-8")
        click.echo(f"Written to {output}", err=True)
    else:
        click.echo(content)


def _configure_logging(level_name: str) -> None:
    """Configure root logger for the CLI session."""
    numeric = getattr(logging, level_name.upper(), logging.WARNING)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _serialize_pydantic(obj: object) -> object:
    """Convert a pydantic model (or list of models) to JSON-serialisable dicts."""
    if isinstance(obj, list):
        return [_serialize_pydantic(item) for item in obj]  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType]
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
    return obj


# ---------------------------------------------------------------------------
# Main CLI group
# ---------------------------------------------------------------------------


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--base-url",
    envvar="NEXTPDF_BASE_URL",
    required=True,
    help="NextPDF server URL (env: NEXTPDF_BASE_URL).",
)
@click.option(
    "--api-key",
    envvar="NEXTPDF_API_KEY",
    required=True,
    help="API key for authentication (env: NEXTPDF_API_KEY).",
)
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error"], case_sensitive=False),
    default="warning",
    show_default=True,
    help="Logging verbosity.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write output to a file instead of stdout.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit 1 on heuristic / low-confidence results (reserved for future use).",
)
@click.pass_context
def main(
    ctx: click.Context,
    base_url: str,
    api_key: str,
    log_level: str,
    output: str | None,
    strict: bool,
) -> None:
    """NextPDF CLI - PDF extraction and semantic analysis for AI agents."""
    _configure_logging(log_level)
    ctx.ensure_object(dict)
    ctx.obj["base_url"] = base_url
    ctx.obj["api_key"] = api_key
    ctx.obj["output"] = output
    ctx.obj["strict"] = strict


# ---------------------------------------------------------------------------
# version command — does NOT require --base-url / --api-key
# ---------------------------------------------------------------------------


@main.command("version")
def version_cmd() -> None:
    """Print the NextPDF SDK version."""
    click.echo(f"nextpdf {__version__}")


# Make --base-url and --api-key optional when running `nextpdf version`.
# We achieve this by making the main group tolerate missing values: the
# options are marked required=True, but Click evaluates them before the
# subcommand is known.  To work around this we override the main group's
# invoke so that only non-version subcommands validate the credentials.

_original_main_invoke = main.invoke


def _patched_main_invoke(ctx: click.Context) -> object:
    """Allow 'version' to skip credential validation."""
    # Resolve which subcommand is being invoked.
    # ctx.protected_params contains the subcommand name for groups.
    invoked = ctx.invoked_subcommand
    if invoked == "version":
        # Provide dummy values so the main group callback doesn't crash.
        ctx.params.setdefault("base_url", "")
        ctx.params.setdefault("api_key", "")
        ctx.params.setdefault("log_level", "warning")
        ctx.params.setdefault("output", None)
        ctx.params.setdefault("strict", False)
    return _original_main_invoke(ctx)


main.invoke = _patched_main_invoke  # type: ignore[method-assign]

# Override required so click does not abort before parsing subcommand
for param in main.params:
    if isinstance(param, click.Option) and param.name in ("base_url", "api_key"):
        param.required = False


# ---------------------------------------------------------------------------
# extract group
# ---------------------------------------------------------------------------


@main.group("extract")
@click.pass_context
def extract_group(ctx: click.Context) -> None:
    """Extract structured content from a PDF."""
    ctx.ensure_object(dict)


# -- extract text -----------------------------------------------------------


@extract_group.command("text")
@click.argument("pdf_path")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "plain"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--page",
    type=int,
    default=None,
    help="Extract only from this 0-based page index.",
)
@click.option(
    "--headings-only",
    is_flag=True,
    default=False,
    help="Extract only heading nodes.",
)
@click.pass_context
def extract_text_cmd(
    ctx: click.Context,
    pdf_path: str,
    fmt: str,
    page: int | None,
    headings_only: bool,
) -> None:
    """Extract cited text blocks from a PDF.

    PDF_PATH is a file path or '-' to read from stdin.
    """
    obj: dict[str, Any] = ctx.obj
    try:
        pdf_data = _read_pdf(pdf_path)
        client = _build_client(obj["base_url"], obj["api_key"])
        blocks = client.ast.extract_cited_text(
            pdf_data,
            page_index=page,
            headings_only=headings_only,
        )

        if fmt == "json":
            content = json.dumps(_serialize_pydantic(blocks), indent=2, ensure_ascii=False)
        elif fmt == "markdown":
            lines: list[str] = []
            for block in blocks:
                page_idx = block.citation.page_index
                node_type_label = f" ({block.node_type})" if block.node_type else ""
                conf = f"{block.citation.confidence:.0%}"
                lines.append(f"[p{page_idx}]{node_type_label} {block.text}  ")
                lines.append(f"  _cite: {block.citation.node_id} conf={conf}_")
                lines.append("")
            content = "\n".join(lines)
        else:
            # plain
            content = "\n".join(block.text for block in blocks)

        _write_output(content, obj.get("output"))
    except NextPDFError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)
    except Exception as exc:
        logger.debug("Unexpected error", exc_info=True)
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)


# -- extract tables ---------------------------------------------------------


@extract_group.command("tables")
@click.argument("pdf_path")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "csv"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--page-start",
    type=int,
    default=None,
    help="Start page index (0-based) for table extraction.",
)
@click.option(
    "--page-end",
    type=int,
    default=None,
    help="End page index (0-based) for table extraction.",
)
@click.pass_context
def extract_tables_cmd(
    ctx: click.Context,
    pdf_path: str,
    fmt: str,
    page_start: int | None,
    page_end: int | None,
) -> None:
    """Extract tables from a PDF.

    PDF_PATH is a file path or '-' to read from stdin.
    """
    obj: dict[str, Any] = ctx.obj
    try:
        pdf_data = _read_pdf(pdf_path)
        client = _build_client(obj["base_url"], obj["api_key"])

        page_range: dict[str, int] | None = None
        if page_start is not None or page_end is not None:
            page_range = {}
            if page_start is not None:
                page_range["start"] = page_start
            if page_end is not None:
                page_range["end"] = page_end

        response = client.ast.extract_cited_tables(pdf_data, page_range=page_range)

        if fmt == "json":
            content = json.dumps(
                _serialize_pydantic(response),
                indent=2,
                ensure_ascii=False,
            )
        else:
            # CSV: one CSV block per table, separated by blank line
            buf = io.StringIO()
            writer = csv.writer(buf)
            for table_idx, table in enumerate(response.tables):
                if table_idx > 0:
                    buf.write("\n")
                writer.writerow([f"# Table {table_idx + 1} (p{table.page_index})"])
                for row in table.rows:
                    writer.writerow([cell.text or "" for cell in row])
            content = buf.getvalue()

        _write_output(content, obj.get("output"))
    except NextPDFError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)
    except Exception as exc:
        logger.debug("Unexpected error", exc_info=True)
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)


# ---------------------------------------------------------------------------
# ast command
# ---------------------------------------------------------------------------


@main.command("ast")
@click.argument("pdf_path")
@click.option(
    "--page-start",
    type=int,
    default=None,
    help="Start page index (0-based).",
)
@click.option(
    "--page-end",
    type=int,
    default=None,
    help="End page index (0-based).",
)
@click.option(
    "--token-budget",
    type=int,
    default=None,
    help="Approximate token limit for the returned AST.",
)
@click.pass_context
def ast_cmd(
    ctx: click.Context,
    pdf_path: str,
    page_start: int | None,
    page_end: int | None,
    token_budget: int | None,
) -> None:
    """Get the full semantic AST of a PDF as JSON.

    PDF_PATH is a file path or '-' to read from stdin.
    """
    obj: dict[str, Any] = ctx.obj
    try:
        pdf_data = _read_pdf(pdf_path)
        client = _build_client(obj["base_url"], obj["api_key"])
        doc = client.ast.get_document_ast(
            pdf_data,
            page_range_start=page_start,
            page_range_end=page_end,
            token_budget=token_budget,
        )
        content = json.dumps(
            _serialize_pydantic(doc),
            indent=2,
            ensure_ascii=False,
        )
        _write_output(content, obj.get("output"))
    except NextPDFError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)
    except Exception as exc:
        logger.debug("Unexpected error", exc_info=True)
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)


# ---------------------------------------------------------------------------
# info command
# ---------------------------------------------------------------------------


@main.command("info")
@click.argument("pdf_path")
@click.pass_context
def info_cmd(ctx: click.Context, pdf_path: str) -> None:
    """Show document info (page count, structure) as JSON.

    PDF_PATH is a file path or '-' to read from stdin.
    """
    obj: dict[str, Any] = ctx.obj
    try:
        pdf_data = _read_pdf(pdf_path)
        client = _build_client(obj["base_url"], obj["api_key"])
        doc = client.ast.get_document_ast(pdf_data)
        info: dict[str, Any] = {
            "schema_version": doc.schema_version,
            "source_hash": doc.source_hash,
            "page_count": doc.page_count,
            "estimated_tokens": doc.estimated_tokens,
            "root_node_type": doc.root.type.value,
            "root_children_count": len(doc.root.children),
        }
        content = json.dumps(info, indent=2, ensure_ascii=False)
        _write_output(content, obj.get("output"))
    except NextPDFError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)
    except Exception as exc:
        logger.debug("Unexpected error", exc_info=True)
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)
