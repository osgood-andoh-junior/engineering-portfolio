# Verification report

Verified on 2026-10-09 using Python 3.12.14, Node.js 24.15.0, Next.js 16.4.0,
React 19.3.0, and Vitest 5.0.3.

| Check | Result |
| --- | --- |
| Backend and ML dependencies | Installed in the project virtual environment |
| Frontend dependencies | Installed; package-lock.json records resolved versions |
| Editable local Python package | Installed; backend and ML modules are importable |
| Backend tests | 36 passed |
| Frontend tests | 11 passed across two test files |
| Frontend/backend integration | Passed against a real, temporary FastAPI process and SQLite database |
| Python lint | Ruff passed |
| Frontend lint | ESLint passed with no errors or warnings |
| TypeScript | Standalone typecheck and build typecheck passed |
| Production build | Passed; all six requested pages generated |
| Backend startup | Uvicorn started successfully on 127.0.0.1:8000 |
| SQLite initialization | backend/storage/support.db created; health reported database sqlite |
| Live prediction endpoint | HTTP 501 with STUDENT_ML_NOT_IMPLEMENTED and component naive_bayes |
| Training stubs | All five registered classifier choices return HTTP 501 and persist failed runs |
| Notebook validation | All six notebooks validated with nbformat; code cells are unexecuted placeholders |
| ML scaffold audit | All 19 function/method bodies are raising stubs; concrete classifiers remain empty |
| ML implementation search | No NumPy, pandas, scikit-learn, neural-framework, or LLM imports in application/core code |
| Browser inspection | Dashboard rendered successfully; live Classify form displayed the backend development error |
| Production npm audit | Zero vulnerabilities |
| Full npm audit | Five high-severity advisories remain in the development lint dependency chain |

## Scope and evidence

Backend coverage includes CRUD, request validation, database constraints, rollback, persistence,
foreign keys, model registry, evaluation storage, missing/outside artifact paths, classifier
contract substitution, invalid output rejection, failed training, and CORS.

Frontend coverage includes empty/error states, ticket creation/edit/deletion, classification
request and result rendering, retained-ticket error messaging, training errors, model empty
states, six experiment cards, and an actual HTTP integration test. All fixture predictions
and metrics exist only inside tests. The application's database remains empty.

The initial test runs exposed local sandbox permissions, pytest's shared temporary folder,
two reused mock Response objects, and one lint issue in the loading effect. These were fixed
before the passing final runs. Pytest uses the dedicated project-local .test-tmp directory.

The embedded browser first failed to attach; a documented retry succeeded. The normal
viewport dashboard was visually inspected, and the classification form was submitted with
saving disabled. It displayed the exact development error and no result. Automated responsive
viewport testing was not performed.

The remaining npm advisories concern the development ESLint/Next lint glob dependency chain
(braces, micromatch, fast-glob, and their consumers). Runtime dependencies have no reported
advisories. No forced downgrade of the current Next.js lint configuration was applied.
The backend test client emits one upstream httpx deprecation warning; all tests pass.

## Student ML boundary

No preprocessing, tokenization, vocabulary, feature representation, probability-estimation,
smoothing, classifier, similarity, embedding, RNN, attention, Transformer, or evaluation
algorithm was implemented. Backend probability checks validate the interface contract only.
All student placeholders remain untouched.

The source tree and every student marker, grouped by experiment, are printed by
scripts/audit_scaffold.py and saved in SCAFFOLD_INVENTORY.md. Shared methods and infrastructure
error-message references are listed separately. The audit is for this initial scaffold and
is expected to fail after student implementations are added.
