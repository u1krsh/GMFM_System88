# GMFM App Architecture

## Technology Choices
- **Language & Runtime:** Python 3.11+
- **UI Toolkit:** KivyMD for a modern, touch-friendly interface that works on desktop and tablets. Main entry managed via `MDApp` with `.kv` layout definitions.
- **Persistence:** SQLite (via `sqlite3`) with a migration helper. Offline-first by default; future sync adapter can hook into `services.sync_service`.
- **PDF & Charts:** ReportLab for deterministic PDF generation, Matplotlib for small trend charts rendered to PNG buffers and embedded in UI + reports.
- **Validation:** Pydantic models for incoming data (patients, sessions, raw GMFM item scores) to keep logic testable.
- **Security:** Field-level encryption using the `cryptography` package (Fernet). Encryption key stored in OS keyring or `.env` fallback for development.
- **Testing:** Pytest with fixtures that spin up an in-memory SQLite database for repeatable scoring/storage tests.

## Package Layout (`src/gmfm_app`)
```
├── app.py                 # KivyMD application bootstrap
├── main.kv                # Root UI description (screen manager, nav)
├── data
│   ├── database.py        # Connection factory, migrations
│   ├── models.py          # Dataclasses + Pydantic schemas
│   └── repositories.py    # CRUD helpers (patients, sessions)
├── scoring
│   ├── constants.py       # Item metadata for GMFM-66 & GMFM-88
│   ├── engine.py          # Shared logic, scoring utilities
│   ├── gmfm66.py          # Scale-specific calculations
│   └── gmfm88.py          # Scale-specific calculations
├── services
│   ├── scoring_service.py # Orchestrates scoring + validation
│   ├── report_service.py  # Builds PDFs and embeds charts
│   ├── chart_service.py   # Creates matplotlib images for domains
│   ├── sync_service.py    # Placeholder for future remote sync
│   └── security.py        # Encryption helpers, key loading
├── ui
│   ├── screens
│   │   ├── patient_form.py
│   │   ├── session_form.py
│   │   ├── session_detail.py
│   │   └── dashboard.py
│   └── widgets.py         # Shared UI components
└── utils
    ├── validation.py      # Extra validation helpers
    └── formatting.py      # PDF & UI formatting utilities
```

Tests live under `tests/` mirroring the runtime packages for clarity.

## Data Flow Overview
1. Clinician creates/updates a **Patient** in the dashboard. Input validated through Pydantic models and encrypted (name, date of birth, identifiers) before persistence.
2. Clinician records a **Session**: selects scale (GMFM-66 or -88), inputs item scores (0-3). Validation ensures completeness per dimension.
3. **Scoring Service** routes to the relevant scale module that:
   - Normalizes raw item inputs.
   - Calculates dimension percentages.
   - Applies lookup tables (GMFM-66 item difficulty) when needed.
   - Returns totals + percentile approximations.
4. **Charts**: Matplotlib plots per-domain trends pulled from stored sessions for the patient. Rendered to PNG buffers for UI cards and PDF embed.
5. **PDF Report**: ReportLab template summarizing patient info, latest session, dimension breakdown, charts, and raw tables. Saved to `reports/` and optionally opened via system viewer.

## Security & Privacy
- Encryption key resolved via `keyring` -> env var fallback -> generated dev key stored in `.env.local` (ignored). All sensitive columns stored encrypted at rest.
- At-rest DB file stored under OS-specific app dir. Optional OS-level file-system encryption recommended for production deployments.
- Future sync module will hash patient identifiers before network transfer.

## Offline-first + Sync Strategy
- All CRUD operations hit SQLite. Sync service exposes `export_payload()` and `apply_remote_changes()` stubs to be filled when a backend exists.
- Database migrations handled by a lightweight version table; upgrade scripts live in `data/migrations` (simple SQL files applied sequentially).

## Testing Strategy
- **Unit tests** for scoring logic with canonical GMFM sample data.
- **Repository tests** using in-memory SQLite + test key for encryption.
- **PDF smoke test** verifying PDF bytes are produced and contain expected text tokens.
- **UI smoke test** using Kivy's test harness to instantiate screens without rendering when possible.

## CLI & Entry Points
- `python -m gmfm_app.app` launches the Kivy UI.
- `python -m gmfm_app.cli export --patient PATIENT_ID` (future) to dump JSON/PDF.

This document should evolve as features land; keep module-specific details near the implementation for clarity.
