# Percentage Planned Complete App

Desktop app for comparing two Primavera P6 `.xer` schedules and calculating planned-vs-actualized starts and finishes for the `Preconstruction` and `Construction` WBS branches.

## What It Does

- Loads a previous and current XER file from a desktop window.
- Reads the project data date from each file.
- Finds activities in the previous update that were planned to start or finish between the two data dates.
- Checks the current update to see whether those activities were actually started or finished.
- Also counts activities that actually started or finished in the current update during the same window, even if they were not planned for that window in the previous update.
- Matches activities by `Activity ID` first, then falls back to `Activity Name`.
- Excludes any activities that are not `Task Dependent`.
- Runs the analysis separately for the `Preconstruction` and `Construction` WBS branches.
- Shows summary tables, detailed activity lists, and charts with:
  - planned count
  - planned and actualized count
  - total actualized count
  - unplanned actualized count
  - planned completion percentage
  - planned share of total actualized percentage
- Splits detailed starts and finishes into separate `actualized planned` and `actualized unplanned` tables.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

## Package As Windows EXE

On Windows:

```bash
py -m pip install -r requirements.txt pyinstaller
py -m PyInstaller --noconfirm --onefile --windowed --name PPCAnalyzer app.py
```

The executable will be created in `dist/PPCAnalyzer.exe`.

## Build With GitHub Actions

This project includes a GitHub Actions workflow at `.github/workflows/build-desktop-app.yml`.

After pushing the project to GitHub:

1. Push to the `main` branch, or run the workflow manually from the GitHub `Actions` tab.
2. Open the `Build Desktop App` workflow run.
3. Download the generated artifacts:
   - `PPCAnalyzer-windows`
   - `PPCAnalyzer-macos`

The Windows artifact contains `PPCAnalyzer.exe`.
The macOS artifact contains a zip file with both `PPCAnalyzer.app` and its required support folder. Keep them together after extracting.

## Current Assumptions

- The project data date is read from the `PROJECT` table, using `last_recalc_date` first and then fallback fields if needed.
- Planned starts use `target_start_date`.
- Planned finishes use `target_end_date`.
- Actual starts use `act_start_date`.
- Actual finishes use `act_end_date`.
- WBS matching is case-insensitive, includes descendants, and tolerates common `Preconstruction` variants such as `Pre-Construction`, `Pre Construction`, and `PRECON`.
