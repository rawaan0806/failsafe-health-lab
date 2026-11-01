# FAILSAFE — AI x Healthcare Hackathon Prototype (v0.8)

> Find the failure points before patients reach them.

FAILSAFE is a synthetic-only workflow stress testing and discrete-event simulation prototype built for DSH Hacks V2. It explores operational discharge bottlenecks, follow-up booking queues, support interventions and staffing options.

**No real patient records are accepted or required. This is not a clinically validated model or decision-support tool.** All inputs, costs and probabilities are illustrative. Its optimization uses exact combinatorial search, **not** a trained predictive healthcare model.

## What it does

- Responsive, English-language landing page at `/`.
- Interactive simulator at `/lab` with synthetic cohort controls.
- Backend routes `POST /api/simulate` and `POST /api/trace`.
- Patient timeline replay, queue pressure, staffing comparisons and budget-constrained intervention optimization.
- Clear scenario limitations, model card and 49 automated regression/hosting tests.

## Publish online with Render

Read **[DEPLOY_NL.md](DEPLOY_NL.md)** for step-by-step Dutch GitHub and Render instructions. The `render.yaml` at the repository root provides an optional one-service Render Blueprint.

Render manual settings:

- Service type: **Web Service**, runtime Python 3, plan Free if available
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 3 --timeout 120 --access-logfile -`
- Health: `/health`

Do not deploy it as an HTML-only static site, because the live Python APIs would be missing.

## Local preview (Windows)

1. Install Python 3.10+.
2. Double-click `START_FAILSAFE_WINDOWS.bat` or run `python server.py`.
3. Open http://127.0.0.1:8765/. The local server is intentionally bound to localhost.

The local script uses only Python's standard library. Production hosting uses Gunicorn (`requirements.txt`).

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Public-demo safeguards

- Strict input validation and request body size limit (16 KB).
- Only an explicit allowlist of public pages and assets. Python source, test files and config files are not web-accessible.
- Public JSON-only, same-origin endpoints. No cross-origin data access.
- Small global API rate cap and a maximum of two simultaneous simulations per server process; callers receive a clear busy response.
- No account data, cookies, database, tracking, external services or real patient files. All data is generated in memory.
- Static pages explicitly disclose synthetic / demonstration status.

The public service is a hackathon demo, not a production hospital system. It does not include authentication or persistent storage. If extending it to real healthcare use, substantial security, privacy, clinical and performance work would be required.

## Project files

- `app.py`: public WSGI web application (for Gunicorn)
- `server.py`: local Python HTTP server and validated simulation interface
- `failsafe.py`, `capacity.py`, `optimizer.py`, `joint_optimizer.py`: simulation and search models
- `index.html`, `lab.html`, `assets/`: website
- `MODEL_CARD.md`, `PROJECT_PITCH.md`, `DEMO_SCRIPT.md`: project notes
- `tests/`: automated regression tests
