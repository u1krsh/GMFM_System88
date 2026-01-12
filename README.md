# MotorMeasure Pro

A cross-platform GMFM-66/88 scoring application for clinicians and therapists. Built with Python and Flet for Android, iOS, and desktop deployment.

---

## Overview

MotorMeasure Pro is an offline-first clinical assessment tool designed to streamline the Gross Motor Function Measure (GMFM) scoring process. It provides accurate GMFM-66 and GMFM-88 scoring pipelines, patient management, session tracking, and comprehensive reporting capabilities.

### Key Features

- **Dual Scale Support** - Complete GMFM-66 and GMFM-88 scoring with all 88 items from the official scoresheet
- **Patient Management** - Dashboard with patient profiles, status tracking, and quick-access actions
- **Session History** - Track assessments over time with session comparison and trend analysis
- **Offline Storage** - Encrypted SQLite database with field-level encryption for patient identifiers
- **PDF Reports** - Generate GMFM scoresheets with marked scores and optional trend charts
- **Cross-Platform** - Native builds for Android, iOS, Windows, macOS, and Linux

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/GMFM_System88.git
   cd GMFM_System88
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r src/requirements.txt
   ```

---

## Usage

### Running the Application

**Desktop:**
```bash
python -m gmfm_app.main
```

**Mobile Build (Android APK):**
```bash
flet build apk --target src/gmfm_app/main.py
```

**Mobile Build (iOS):**
```bash
flet build ipa --target src/gmfm_app/main.py
```

### Workflow

1. Launch the application and create a new patient from the dashboard
2. Select a patient and tap "Start Test" to begin a GMFM assessment
3. Choose between GMFM-66 or GMFM-88 scale
4. Score each item (0-3 or NT) across domains A through E
5. Save the session to persist scores
6. Export PDF reports or view session history for trend analysis

### Generated Files

| Location | Description |
|----------|-------------|
| `reports/` | PDF scoresheets with marked assessments |
| `exports/` | Trend charts and data exports |
| `.gmfm_data/` | Local SQLite database |

---

## Project Structure

```
GMFM_System88/
├── src/
│   └── gmfm_app/
│       ├── main.py           # Application entry point
│       ├── data/             # Database and models
│       ├── scoring/          # GMFM scoring logic
│       ├── services/         # Business logic services
│       └── views/            # UI components
├── tests/                    # Automated test suite
├── docs/                     # Documentation
└── requirements.txt          # Python dependencies
```

---

## Security

MotorMeasure Pro implements multiple layers of security for patient data protection:

- **Encryption at Rest** - Patient names and identifiers are encrypted in the SQLite database
- **Key Management** - Encryption keys are resolved from environment variables, OS keyring, or generated fallback
- **Local Storage** - All data remains on-device with no external network calls

### Configuration

Set the encryption key via environment variable:
```bash
export GMFM_APP_SECRET="your-secure-key-here"
```

Alternatively, the application will use the OS keyring or generate a local key file.

---

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

Or using unittest:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Dependencies

| Package | Purpose |
|---------|---------|
| flet | Cross-platform UI framework |
| pydantic | Data validation and models |
| cryptography | Field-level encryption |

---

## Roadmap

- Remote sync adapter for multi-device support
- Role-based access control for clinical teams
- GMFCS classification integration
- Automated deployment packages

---

## License

This project is proprietary software. All rights reserved.

---

## Acknowledgments

Based on the Gross Motor Function Measure (GMFM) developed by Dianne Russell, Peter Rosenbaum, and colleagues at CanChild Centre for Childhood Disability Research, McMaster University.
