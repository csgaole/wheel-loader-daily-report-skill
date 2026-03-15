# wheel-loader-daily-report-skill

OpenClaw wheel loader daily report skill and project files.

## Included
- `loader_intel/` - collection, analysis, reporting, PDF generation, and Feishu delivery
- `skills/loader-daily-report-skill/` - skill wrapper and usage docs

## Current delivery chain
`reporter.py` is the single supported implementation for:
- generating Markdown
- generating PDF
- copying Chinese-named PDF
- sending the PDF to Feishu
