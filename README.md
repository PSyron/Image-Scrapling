# SVG Scrapling

Repository for discovering, evaluating, converting, and cataloging coloring-style image assets.

## Bootstrap

Run the standard project commands from the repository root:

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src apps
uv run pytest
```

## Current Runtime Note

The VTracer conversion backend is currently supported on Python `>=3.10,<3.14`. The Python `3.14` compatibility follow-up is tracked in GitHub issue `#20`.

## Developer Workflow

Repository workflow, validation expectations, and run output conventions are documented in [docs/developer-workflow.md](docs/developer-workflow.md).
