# BlueGrid backend

Flask app (API, planner pages, PDF export) and the optimisation engine, managed with
[uv](https://docs.astral.sh/uv/). Its Python environment is `backend/.venv`; see the
[project README](../README.md) for the full guide.

```bash
cd backend
uv sync                              # create/update .venv from uv.lock (Python 3.10)
uv run flask --app run:app run       # serve the globe + planner at http://127.0.0.1:5000
uv run pytest                        # tests
```
