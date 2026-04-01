# nextpdf Examples

Example scripts demonstrating common nextpdf usage patterns.

## Prerequisites

Install nextpdf:

```bash
pip install nextpdf
```

For all examples using the remote backend, you need a running NextPDF Connect server:

```bash
docker run -p 8080:8080 nextpdf/connect:latest
```

## Examples

| File | Description |
|------|-------------|
| `basic_extract_text.py` | Extract text blocks with citation anchors |
| `basic_extract_tables.py` | Extract tables with cell-level citations |
| `async_batch.py` | Process multiple PDFs concurrently with async client |
| `local_backend.py` | Use the local pypdf backend (no server required, beta) |
| `cli_usage.sh` | Common CLI commands for shell scripting |

## Running

```bash
# Set your server connection (or pass inline)
export NEXTPDF_BASE_URL=http://localhost:8080
export NEXTPDF_API_KEY=your-key

# Run any example
python examples/basic_extract_text.py path/to/document.pdf
```
