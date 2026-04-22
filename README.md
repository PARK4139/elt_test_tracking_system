# elt_test_tracking_system

Internal ELT test tracking system MVP.

## Primary Startup Path (Windows)

The primary startup flow is:

1. `run.cmd`
2. `run.py`
3. FastAPI application startup

Run:

```cmd
run.cmd
```

## Setup

Install dependencies with `uv`:

```cmd
uv sync
```

## Notes

- This is a minimal server-side rendered MVP (FastAPI + Jinja2 + SQLite + SQLAlchemy).
- The `test_result` row supports partial updates to allow progressive multi-turn tester input.
- Excel export exists as an admin placeholder endpoint.
