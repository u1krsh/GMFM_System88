# GMFM Companion

Offline-first GMFM-66/88 scoring companion for clinicians. Ships with a KivyMD UI, encrypted SQLite storage, PDF summaries, and charting utilities.

## Features (MVP)
- Accurate, testable GMFM-66 and GMFM-88 scoring pipeline backed by the official score sheet catalog (all 88 items).
- Patient dashboard with status chips, last-score context, and one-tap “Test” / “Test Again” / “View Sessions” actions.
- GMFM score sheet UI that mirrors the paper form – domains A–E, score columns (0–3) plus NT, and live summary math.
- Field-level encryption for sensitive patient identifiers with offline SQLite storage.
- PDF exports that reproduce the GMFM-66/88 sheet with “X” marks in the proper score/NT columns plus optional trend charts.

## Security
- Encryption keys resolved from `GMFM_APP_SECRET`, OS keyring, or generated `.env.local` fallback.
- Patient names and identifiers are encrypted at rest inside SQLite.
- Local filesystem folders (`reports/`, `exports/`) are created on launch; protect them with OS-level encryption for production.

## Getting Started
1. **Create and activate** a Python 3.11+ environment.
2. **Install dependencies**:
   ```bash
   pip install -e .[dev]
   ```
3. **Run the app**:
   ```bash
   python -m gmfm_app.app
   ```
4. **Run the tests**:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```

## Using the App
1. Launch the Kivy UI and create a patient from the toolbar (top-right `+` icon).
2. From the dashboard, tap **Start Test/Test Again** on a patient row to open the full GMFM score sheet.
3. Choose **GMFM-66** or **GMFM-88** with the chips, then tap the score buttons (0–3 or **NT**) for each item the way you would on the paper sheet. A live summary of domain percentages appears underneath.
4. Press **Save Session** to persist the assessment, or **Save & Export PDF** to immediately generate a GMFM sheet PDF with every scored item marked in-place (files land in `reports/`).
5. Use **View Sessions** on any patient to browse history, render charts, or export the latest session again.
6. Generated artifacts:
   - Trend charts saved to `exports/patient_<id>_trend.png`.
   - GMFM score sheets saved to `reports/patient_<id>_session_<id>.pdf`.

> The UI uses Kivy; make sure you have the required system dependencies per the [Kivy installation guide](https://kivy.org/doc/stable/installation/installation.html).

## Repository Layout
- `src/gmfm_app/` – application source
- `tests/` – pytest-based automated tests
- `docs/` – architecture and planning documents

## Roadmap
- Remote sync adapter
- Role-based access control
- Automated deployment bundles (Windows/macOS)
