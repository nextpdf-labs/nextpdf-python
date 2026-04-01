#!/usr/bin/env bash
# NextPDF CLI examples
#
# Prerequisites:
#   pip install nextpdf
#   export NEXTPDF_BASE_URL=http://localhost:8080
#   export NEXTPDF_API_KEY=your-key
#
# Or pass --base-url and --api-key inline with each command.

set -euo pipefail

# --- Extract text as JSON (default format) ---
nextpdf extract text document.pdf \
  --base-url http://localhost:8080 \
  --api-key your-key

# --- Extract text as plain text ---
nextpdf extract text document.pdf --format plain

# --- Extract text as markdown with citation annotations ---
nextpdf extract text document.pdf --format markdown

# --- Extract only headings ---
nextpdf extract text document.pdf --headings-only

# --- Extract text from a specific page (0-based index) ---
nextpdf extract text document.pdf --page 0

# --- Extract tables as JSON ---
nextpdf extract tables invoice.pdf

# --- Extract tables as CSV ---
nextpdf extract tables invoice.pdf --format csv

# --- Extract tables from a page range ---
nextpdf extract tables invoice.pdf --page-start 0 --page-end 5

# --- Get the full semantic AST as JSON ---
nextpdf ast document.pdf

# --- Get AST for a page range with token budget ---
nextpdf ast document.pdf --page-start 0 --page-end 10 --token-budget 4000

# --- Get document info (page count, structure summary) ---
nextpdf info document.pdf

# --- Write output to a file ---
nextpdf extract text document.pdf -o output.json

# --- Read PDF from stdin ---
cat document.pdf | nextpdf extract text -

# --- Check SDK version (no server required) ---
nextpdf version

# --- Enable debug logging ---
nextpdf --log-level debug extract text document.pdf
