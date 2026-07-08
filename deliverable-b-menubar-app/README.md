# Deliverable B — macOS Menu Bar Helper

A standalone menu-bar app that clicks the Naviga Ad Extension's Refresh button
inside Adobe InDesign on a configurable timer. Does not modify any Naviga files.

## Requirements

- macOS 12+
- Python 3.9+
- Adobe InDesign must be open with the Naviga panel visible

## Setup

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Run

```bash
venv/bin/python3 naviga_helper.py
```

A "N⚡" icon appears in the macOS menu bar.

## First-Time Permissions

macOS will prompt for Accessibility access the first time a click is attempted.
Go to: System Settings → Privacy & Security → Accessibility → enable Terminal
(or your Python interpreter).

## Menu Options

- **Auto-Refresh: OFF/ON** — toggle the refresh timer
- **Auto-Claim: OFF/ON** — toggle auto-clicking "Assign this to me" after each refresh
- **Interval** — choose 5s / 10s / 30s / 60s between refreshes
- **Status** — shows last action and elapsed time
- **Quit** — stops the app

## Behavior Notes

- Auto-Refresh pauses automatically if InDesign is not the frontmost app
- Auto-Claim uses Accessibility API to find the "Assign this to me" button;
  if the AX tree doesn't expose it (common in CEP panels), claim will not fire
- Settings are saved to `naviga_helper_settings.json` in this folder

## TOS Note

This tool does not modify any Naviga files. It simulates user mouse clicks
at the OS level. Review Naviga's TOS regarding automated UI interaction
before deploying in production.
