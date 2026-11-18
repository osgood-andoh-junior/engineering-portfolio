# NLP Support-Ticket Intelligence System

A local educational multiclass text-classification project. The software infrastructure works;
the NLP and ML implementations belong to you.

## Requirements

Python 3.11+ and Node.js 22.12+. Run backend commands from this project
root. Use a separate terminal for the frontend. No external ML service, Docker, or cloud
account is required.

## Setup — Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
cd frontend
npm ci
```

If Python is launched through `py` on your computer, use `py -3 -m venv .venv` for the first
command. The generated project already has its dependencies installed in `.venv` and
`frontend/node_modules`; the commands above document a fresh installation.

macOS/Linux: use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows Python
path. Copy environment files using `cp`. The remaining commands are the same.

`requirements.txt` installs both backend and laboratory dependencies. To install the backend
alone, use `backend/requirements.txt`. `requirements.lock.txt` records the complete Python
environment used for verification on Windows; portable version ranges remain in the
requirements files. The frontend uses `package-lock.json`.

## Run

Backend, from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm run dev
```

Open [the dashboard](http://localhost:3000), [API documentation](http://localhost:8000/docs),
or [health](http://localhost:8000/health).

SQLite initializes automatically on backend startup at `backend/storage/support.db`.
Artifacts belong in `ml/artifacts/`. Both are ignored by Git. Backend paths in `.env` resolve
relative to the project root; absolute paths also work. Next.js reads its own
`frontend/.env.local`; restart it after changing `NEXT_PUBLIC_API_URL`.
`FRONTEND_ORIGIN` must match the browser origin for CORS.

## What works now

- Six responsive pages: Dashboard, Tickets, Classify Ticket, Training, Models, Experiments.
- Create, list, inspect, edit, and delete tickets. Optional actual labels use six categories.
- SQLite persistence for tickets, models, evaluations, and training attempts.
- Swappable classifier contract and an artifact-aware registry.
- Clean HTTP 501 development errors for unimplemented prediction or training.
- Failed training attempts recorded without registering a model.
- Honest empty states: no seeded tickets, fabricated predictions, or invented metrics.

Creating a ticket does not classify it. The Classify page can first save the ticket; that
record remains if classification fails. With saving disabled, classification is transient.
Changing a saved ticket's text clears its previous prediction.

The most recently registered model is the current inference model. An API caller can select
a particular registered version. Training is synchronous and uses labeled tickets. It does
not split datasets or calculate evaluations: those are student work. Empty-data handling
belongs to the student training implementation; the initial stubs always raise the development
error, including for an empty dataset.

## API

| Method | Route | Behavior |
| --- | --- | --- |
| GET | /health | Check service and database |
| POST | /api/tickets | Create text and optional actual_category |
| GET | /api/tickets | List tickets, newest first |
| GET | /api/tickets/{id} | Read ticket |
| PATCH | /api/tickets/{id} | Update text and/or actual_category |
| DELETE | /api/tickets/{id} | Delete ticket |
| POST | /api/predictions | Supply exactly one of text or ticket_id; optional model_version |
| POST | /api/training/start | Supply model, default naive_bayes |
| GET | /api/training/runs | Read persisted attempts |
| GET | /api/models | Read registered model versions |
| GET | /api/evaluations | Read student-produced metrics |

Unimplemented ML returns HTTP 501:

```json
{
  "error": "STUDENT_ML_NOT_IMPLEMENTED",
  "component": "naive_bayes",
  "message": "Complete TODO(STUDENT-ML) in the ML module."
}
```

Validation errors use HTTP 422; missing records use 404; missing artifacts use 409; invalid
classifier outputs use 502. The app never falls back to a guess.

## Student workflow

1. Start JupyterLab using the environment: `.venv/Scripts/jupyter-lab.exe` on Windows or
   `.venv/bin/jupyter-lab` on macOS/Linux.
2. Open `ml/notebooks/01_bow_naive_bayes.ipynb`.
3. Work through [the learning path](docs/ML_LEARNING_PATH.md). Implement reusable ML in
   `ml/src/`; put your tests in `ml/tests/`.
4. Satisfy `ml/src/interfaces.py`: fit, predict, predict_proba, save, load. Each implementation
   receives raw text; its internal preprocessing and representation are your responsibility.
   `load(path)` initializes the current instance and returns nothing. `save(path)` must write
   the artifact file at the supplied path. Probability output contains one mapping per
   input with all six category keys, finite values in [0, 1], and total probability 1.
5. Start training from the UI after implementing the chosen classifier. Successful training
   writes an artifact and registers the version. TF-IDF is a representation experiment;
   use it inside your chosen classifier rather than a separate backend service.
6. Compute your evaluation independently, then write a JSON object with numeric keys
   `accuracy`, `precision`, `recall`, `f1` in [0, 1]. Import it:
   `python -m backend.app.cli YOUR_REGISTERED_VERSION path/to/your-metrics.json`
   using the activated environment, or the explicit virtual-environment Python path.
   This command validates and stores values; it does not calculate them.

The registry factories in `backend/app/services/registry.py` connect implementations to the
contract. Add factories and the corresponding API/UI model choice when introducing a new
classifier. Existing route logic does not change.

## Verify

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -X utf8 scripts/audit_scaffold.py
```

From `frontend/`:

```powershell
npm test
npm run lint
npm run typecheck
npm run build
```

Frontend tests include a real temporary FastAPI process and SQLite database. They discover
Python from the root `.venv`; set `TEST_PYTHON` to override it. Component fixtures and the
backend contract test doubles are isolated test data, never application fallback behavior.
The scaffold audit validates empty notebooks, verifies unimplemented ML bodies, and prints
the source tree and every ML marker grouped by experiment. It also lists infrastructure
references. It is an initial-delivery audit: it intentionally fails after you implement ML.

See [architecture](docs/ARCHITECTURE.md), [verification](docs/VERIFICATION.md), and the generated
[tree and TODO inventory](docs/SCAFFOLD_INVENTORY.md).

## V1 scope

This is a local single-user learning app, with no authentication or deployment setup.
Ticket and registry lists are intentionally unpaginated. There is no background training
queue or cancellation. Avoid simultaneous training requests and use small learning datasets.
Only load artifacts you created and trust. Keep private ticket data out of version control.

Start with Experiment 01: Bag of Words + Naive Bayes.
