# elt_test_tracking_system

Internal ELT test tracking system MVP.

## Setup

Install dependencies with uv:

```bash
uv sync
```

## Run

Primary startup path (keep this flow):
1. `run.cmd`
2. `run.py`
3. FastAPI app startup

```cmd
run.cmd
```

Direct uv run path:

```bash
uv run python run.py
```

## Notes

- This is a minimal server-side rendered MVP (FastAPI + Jinja2 + SQLite + SQLAlchemy).
- The `test_result` row supports partial updates to allow progressive multi-turn tester input.
- Excel export exists as an admin placeholder endpoint.
