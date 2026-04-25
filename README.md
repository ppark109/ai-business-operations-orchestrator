# AI FlowOps

AI-first workflow automation for commercial intake, risk routing, operational
handoff, human approval, and KPI-driven process improvement.

This project showcases how a regular business process can be redesigned as an
AI-managed operation. The system turns a messy commercial intake package into a
structured case file, extracts evidence-backed obligations and risks, compares
them against a declarative playbook, routes the case to the right function,
pauses for human approval when needed, and records outcomes for evals and KPI
tracking.

## MVP Scope

- Five routes: auto-approval, legal, security, implementation, and finance.
- Structured case files backed by Pydantic schemas.
- Declarative playbook rules for inspectable business policy.
- Evidence-first extraction and routing workflow.
- Human-in-the-loop approval queue for risky or low-confidence cases.
- Mock downstream task creation instead of real enterprise integrations.
- Trace, eval, and KPI records suitable for regression testing.

## Repository Map

| Path | Purpose |
|---|---|
| `app/` | FastAPI entrypoint, API routes, settings, and future persistence adapters. |
| `agents/` | Specialist agent prompts, configs, and extraction/critic modules. |
| `workflows/` | Orchestration, routing, approval, and playbook logic. |
| `schemas/` | Pydantic models for case files, findings, routing, tasks, and approvals. |
| `playbooks/` | YAML business rules that drive risk, routing, and approval behavior. |
| `data/` | Seed cases, synthetic intake artifacts, held-out eval cases, and local runtime data. |
| `evals/` | Eval configs, graders, datasets, and baseline result artifacts. |
| `dashboard/` | Future review dashboard assets and UI code. |
| `docs/` | Strategy report, architecture diagram, and human-in-the-loop flow chart. |
| `traces/` | Local trace fixtures or exported trace samples. |
| `scripts/` | Dataset, seeding, maintenance, and batch-run helper scripts. |
| `tests/` | Unit, schema, routing, and regression tests. |

## Local Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Run the test suite:

```powershell
pytest
```

Run linting:

```powershell
ruff check .
```

## Project Context

Start with the report and diagrams in `docs/`:

- `docs/system-architecture.png`
- `docs/human-in-the-loop.png`

The first version should stay focused on realistic orchestration quality:
structured inputs, evidence-backed findings, transparent rules, correct routing,
approval governance, traceability, and regression tests.
