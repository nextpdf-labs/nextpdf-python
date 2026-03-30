# nextpdf

Python SDK for [NextPDF](https://nextpdf.dev) — The PDF Runtime for AI Agents.

## Installation

```bash
pip install nextpdf
```

## Quick Start

### Async (recommended)

```python
import asyncio
import nextpdf

async def main() -> None:
    async with nextpdf.AsyncNextPDF(
        base_url="https://your-nextpdf-instance.com",
        api_key="your-api-key",
    ) as client:
        with open("document.pdf", "rb") as f:
            pdf_bytes = f.read()

        ast = await client.ast.get_document_ast(pdf_bytes)
        print(f"Pages: {ast.page_count}, ~{ast.estimated_tokens} tokens")

asyncio.run(main())
```

### Sync

```python
import nextpdf

client = nextpdf.NextPDF(
    base_url="https://your-nextpdf-instance.com",
    api_key="your-api-key",
)

with open("document.pdf", "rb") as f:
    pdf_bytes = f.read()

ast = client.ast.get_document_ast(pdf_bytes)
print(f"Pages: {ast.page_count}, ~{ast.estimated_tokens} tokens")
```

## Error Handling

```python
import nextpdf

try:
    ast = client.ast.get_document_ast(pdf_bytes)
except nextpdf.NextPDFLicenseError:
    print("Upgrade required: https://nextpdf.dev/pricing")
except nextpdf.QuotaExceededError as e:
    print(f"Quota exceeded. Retry after: {e.retry_after}s")
except nextpdf.AstNoStructTreeError:
    print("PDF is untagged — enable heuristic mode (Pro)")
except nextpdf.NextPDFAPIError as e:
    print(f"API error {e.status_code}: {e}")
```

## License

MIT — Free for all use. See [LICENSE](LICENSE).
