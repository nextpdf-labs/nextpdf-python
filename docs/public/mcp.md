---
title: "Python MCP server"
summary: "Expose NextPDF PDF extraction tools to MCP-capable AI agents by running the Python SDK's bundled MCP server."
stability: stable
since: "1.0.0"
deprecated_since: ""
replaced_by: ""
edition: core
audience: [senior]
mode: how-to
version_lifecycle: active
eol_date: ""
prerequisites: ["Python 3.10 or newer", "The nextpdf[mcp] extra installed", "A NextPDF Connect endpoint"]
related: ["/python/overview/", "/python/quickstart/", "/python/cli/"]
citations: []
runnable_example: ""
reproducibility_profile: semantic
output_hash: ""
performance_budget: { wall_ms: 1000, peak_mb: 128 }
compatibility: ["8.4"]
commercial_context:
  core_alternative: ""
  premium_advantage: ""
  conversion_link: ""
source_repo: nextpdf-python
source_ref: main
source_hash: ""
manifest_hash: ""
export_control_class: none
last_reviewed: "2026-05-27"
reviewer: "@nextpdf-docs-team"
publish: false
gated: false
inclusive_language_checked: true
i18n_ready: true
xliff_segments: 0
---

# Python MCP server

Install the SDK with MCP support:

```bash
pip install nextpdf[mcp]
```

Run the server module from your MCP client configuration:

```json
{
  "mcpServers": {
    "nextpdf": {
      "command": "python",
      "args": ["-m", "nextpdf.mcp"],
      "env": {
        "NEXTPDF_BASE_URL": "http://localhost:8080",
        "NEXTPDF_API_KEY": "your-key"
      }
    }
  }
}
```

After registration, an MCP-capable agent can use NextPDF tools such as cited text extraction, cited table extraction, semantic AST retrieval, node search, outline inspection, AST diffing, and document info.

## Operational notes

Point the MCP server at a controlled NextPDF Connect deployment. Treat the API key as a secret and scope it to the workloads that the agent is allowed to perform.

For local experiments, start with a development Connect endpoint. For production agent workflows, run the endpoint behind the same authentication, quota, and observability controls used by other service clients.
