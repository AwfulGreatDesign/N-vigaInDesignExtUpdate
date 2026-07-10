# Naviga Ad Queue Automation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two independent automation tools — a CEP injector (Deliverable A) and a macOS menu-bar app (Deliverable B) — that auto-refresh the Naviga Ad queue every 10 seconds and auto-claim unassigned ads.

**Architecture:** Deliverable A patches the existing Naviga CEP extension's `index.html` to load a new `naviga-auto.js` script that runs inside the panel's Chromium context and calls existing JS functions directly. Deliverable B is a standalone Python menu-bar app that uses macOS Accessibility APIs and coordinate-based clicking to interact with InDesign's Naviga panel without touching any Naviga files.

**Tech Stack:** JavaScript (CEP/Chromium), Python 3.11+, rumps 0.4+, pyobjc-framework-Cocoa, pyobjc-framework-Quartz, bash

## Global Constraints

- All work lives under `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/`
- Naviga extension source: `/Library/Application Support/Adobe/CEP/extensions/NavigaAd/`
- Only `index.html` is modified by Deliverable A — no other Naviga files are touched
- Backup of original files must exist before any modification is made
- Deliverable A and Deliverable B are fully independent — neither depends on the other
- Python minimum version: 3.11
- No external JS dependencies in naviga-auto.js — jQuery is already loaded by the panel
- Auto-Claim defaults to OFF — must be explicitly enabled by the user

---

### Task 0: Back Up Original Naviga Files + Create Changelog Document

**Files:**
- Create: `naviga-originals/client/index.html` (copy)
- Create: `naviga-originals/client/index.js` (copy)
- Create: `naviga-originals/client/CSInterface.js` (copy)
- Create: `deliverable-a-cep-injector/CHANGES.md`

**Interfaces:**
- Produces: `naviga-originals/` directory with pristine copies of all files Deliverable A will reference; `CHANGES.md` changelog stub ready to be filled in by Task 1

- [ ] **Step 1: Create the backup directory structure**

```bash
mkdir -p /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client
```

- [ ] **Step 2: Copy the three Naviga client files**

```bash
cp "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html" \
   /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/index.html

cp "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.js" \
   /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/index.js

cp "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/CSInterface.js" \
   /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/CSInterface.js
```

- [ ] **Step 3: Verify copies are identical to source**

```bash
diff "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html" \
     /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/index.html && echo "index.html OK"

diff "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.js" \
     /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/index.js && echo "index.js OK"

diff "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/CSInterface.js" \
     /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/CSInterface.js && echo "CSInterface.js OK"
```
Expected: three "OK" lines, no diff output.

- [ ] **Step 4: Create the CHANGES.md changelog document**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/CHANGES.md` with this exact content:

```markdown
# Deliverable A — Changes Made to Naviga Extension Files

This document records every change made to files belonging to the Naviga Ad
Extension (`/Library/Application Support/Adobe/CEP/extensions/NavigaAd/`)
as part of the Ballantine auto-refresh/auto-claim automation (Deliverable A).

Pristine copies of all referenced files (before any modification) are preserved in:
`naviga-originals/client/`

---

## Files Modified

### 1. `client/index.html`

**Full path:** `/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html`

**Nature of change:** One line added — a `<script>` tag that loads the
automation patch script. No existing lines were removed or altered.

**Exact change:**

Before (original final lines of `<body>`):
```html
    <script type="text/javascript" src="CSInterface.js"></script>
    <script type="text/javascript" src="index.js"></script>
    <script type="text/javascript">
        ...inline script block...
    </script>
</body>
</html>
```

After (with patch applied):
```html
    <script type="text/javascript" src="CSInterface.js"></script>
    <script type="text/javascript" src="index.js"></script>
    <script type="text/javascript">
        ...inline script block (unchanged)...
    </script>
    <script type="text/javascript" src="naviga-auto.js"></script>
</body>
</html>
```

**Why:** The script tag must appear after `index.js` so that jQuery and all
existing functions (`refresh()`, `assignArtist()`, etc.) are defined before
`naviga-auto.js` runs.

**Effect on existing behavior:** None. The existing inline script block is
untouched. `naviga-auto.js` only adds new behavior on top of existing functions.

---

## Files Added (New — Not Part of Naviga's Original Installation)

### 2. `client/naviga-auto.js`

**Full path:** `/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/naviga-auto.js`

**Nature of change:** New file — does not exist in Naviga's original installation.

**Purpose:** Contains all automation logic — auto-refresh timer, auto-claim
MutationObserver, UI toggle controls, and localStorage persistence.

**Functions defined:**
- `navigaAutoInit()` — entry point, called once on DOMContentLoaded
- `navigaStartRefreshTimer()` — starts/restarts the 10-second setInterval
- `navigaStopRefreshTimer()` — clears the interval
- `navigaStartClaimObserver()` — attaches MutationObserver to unassigned queue tbody
- `navigaStopClaimObserver()` — disconnects the observer
- `navigaInjectControls()` — injects the Auto-Refresh and Auto-Claim checkboxes into the panel UI
- `navigaSaveSettings()` — persists toggle state to localStorage
- `navigaLoadSettings()` — reads toggle state from localStorage on init

**Calls made into existing Naviga functions:**
- `refresh()` — called by the auto-refresh timer (defined in index.html inline script)
- Button `.click()` on `button#assign-indd` — triggered by the MutationObserver

**localStorage keys added (new, no collision with Naviga's existing keys):**
- `naviga_auto_refresh` — `"true"` or `"false"`
- `naviga_auto_claim` — `"true"` or `"false"`

---

## Files NOT Modified

The following Naviga files are referenced/copied for preservation but are
not modified by Deliverable A:

- `client/index.js` — unchanged
- `client/CSInterface.js` — unchanged
- `CSXS/manifest.xml` — unchanged
- `host/index.jsx` — unchanged
- All kendo, remodal, mark assets — unchanged

---

## How to Restore Original State

Option 1 — Run the uninstall script:
```bash
cd /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector
bash uninstall.sh
```

Option 2 — Manual restore:
```bash
cp /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/index.html \
   "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html"

rm "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/naviga-auto.js"
```

Then restart Adobe InDesign.
```

- [ ] **Step 5: Create the deliverable-a directory**

```bash
mkdir -p /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector
```

---

### Task 1: Deliverable A — Write naviga-auto.js

**Files:**
- Create: `deliverable-a-cep-injector/naviga-auto.js`

**Interfaces:**
- Consumes: `refresh()` (defined in NavigaAd's `index.html` inline script), `$` (jQuery, loaded before this script), `button#assign-indd` (DOM element that appears in `#tblProjectLinesUnAssigned tbody` when an unassigned ad is present)
- Produces: `navigaAutoInit()` — called by Task 2's install; `naviga_auto_refresh` and `naviga_auto_claim` localStorage keys

- [ ] **Step 1: Create naviga-auto.js**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/naviga-auto.js` with this content:

```javascript
(function () {
    // ── Configuration ────────────────────────────────────────────────────────
    var AUTO_REFRESH_INTERVAL_MS = 10000;  // 10 seconds
    var CLAIM_DELAY_MS           = 0;      // ms to wait before clicking Assign

    // ── Storage keys (must not collide with Naviga's existing keys) ──────────
    var KEY_AUTO_REFRESH = 'naviga_auto_refresh';
    var KEY_AUTO_CLAIM   = 'naviga_auto_claim';

    // ── Internal state ───────────────────────────────────────────────────────
    var refreshTimer    = null;
    var claimObserver   = null;
    var lastRefreshTime = null;
    var statusEl        = null;

    // ── Settings persistence ─────────────────────────────────────────────────
    function loadSettings() {
        var r = localStorage.getItem(KEY_AUTO_REFRESH);
        var c = localStorage.getItem(KEY_AUTO_CLAIM);
        return {
            autoRefresh: r === null ? true  : r === 'true',
            autoClaim:   c === null ? false : c === 'true'
        };
    }

    function saveSettings(autoRefresh, autoClaim) {
        localStorage.setItem(KEY_AUTO_REFRESH, autoRefresh ? 'true' : 'false');
        localStorage.setItem(KEY_AUTO_CLAIM,   autoClaim   ? 'true' : 'false');
    }

    // ── Status display ───────────────────────────────────────────────────────
    function updateStatus() {
        if (!statusEl) return;
        var settings = loadSettings();
        if (!settings.autoRefresh) {
            statusEl.textContent = 'Auto-refresh: OFF';
            return;
        }
        if (!lastRefreshTime) {
            statusEl.textContent = 'Auto-refresh: ON';
            return;
        }
        var elapsed = Math.floor((Date.now() - lastRefreshTime) / 1000);
        statusEl.textContent = 'Auto-refresh: ON — last: ' + elapsed + 's ago';
    }

    // ── Auto-refresh timer ───────────────────────────────────────────────────
    function startRefreshTimer() {
        stopRefreshTimer();
        refreshTimer = setInterval(function () {
            // Only refresh when user is logged in (logout div is visible)
            if ($('#divLogout').is(':visible')) {
                refresh();
                lastRefreshTime = Date.now();
                updateStatus();
            }
        }, AUTO_REFRESH_INTERVAL_MS);
    }

    function stopRefreshTimer() {
        if (refreshTimer !== null) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }

    // ── Auto-claim observer ──────────────────────────────────────────────────
    function startClaimObserver() {
        stopClaimObserver();
        var target = document.querySelector('#tblProjectLinesUnAssigned tbody');
        if (!target) return;
        claimObserver = new MutationObserver(function () {
            var assignBtn = document.querySelector('button#assign-indd');
            if (assignBtn) {
                setTimeout(function () {
                    assignBtn.click();
                }, CLAIM_DELAY_MS);
            }
        });
        claimObserver.observe(target, { childList: true, subtree: true });
    }

    function stopClaimObserver() {
        if (claimObserver !== null) {
            claimObserver.disconnect();
            claimObserver = null;
        }
    }

    // ── UI controls ──────────────────────────────────────────────────────────
    function injectControls() {
        var logoutDiv = document.getElementById('divLogout');
        if (!logoutDiv) return;

        var wrapper = document.createElement('div');
        wrapper.style.cssText = 'margin-top: 6px; font-size: 75%; color: #aaa;';

        // Auto-Refresh checkbox
        var cbRefresh = document.createElement('input');
        cbRefresh.type    = 'checkbox';
        cbRefresh.id      = 'naviga-auto-refresh-toggle';
        cbRefresh.style.cssText = 'vertical-align: middle; margin-right: 4px;';

        var lblRefresh = document.createElement('label');
        lblRefresh.htmlFor   = 'naviga-auto-refresh-toggle';
        lblRefresh.textContent = 'Auto-Refresh';
        lblRefresh.style.cssText = 'margin-right: 10px; cursor: pointer;';

        // Auto-Claim checkbox
        var cbClaim = document.createElement('input');
        cbClaim.type  = 'checkbox';
        cbClaim.id    = 'naviga-auto-claim-toggle';
        cbClaim.style.cssText = 'vertical-align: middle; margin-right: 4px;';

        var lblClaim = document.createElement('label');
        lblClaim.htmlFor   = 'naviga-auto-claim-toggle';
        lblClaim.textContent = 'Auto-Claim';
        lblClaim.style.cssText = 'cursor: pointer;';

        // Status line
        statusEl = document.createElement('div');
        statusEl.style.cssText = 'margin-top: 4px; font-size: 90%; color: #888; font-style: italic;';

        // Wire up events
        cbRefresh.addEventListener('change', function () {
            var settings = loadSettings();
            saveSettings(cbRefresh.checked, settings.autoClaim);
            if (cbRefresh.checked) {
                startRefreshTimer();
            } else {
                stopRefreshTimer();
            }
            updateStatus();
        });

        cbClaim.addEventListener('change', function () {
            var settings = loadSettings();
            saveSettings(settings.autoRefresh, cbClaim.checked);
            if (cbClaim.checked) {
                startClaimObserver();
            } else {
                stopClaimObserver();
            }
        });

        wrapper.appendChild(cbRefresh);
        wrapper.appendChild(lblRefresh);
        wrapper.appendChild(cbClaim);
        wrapper.appendChild(lblClaim);
        wrapper.appendChild(statusEl);
        logoutDiv.appendChild(wrapper);

        // Apply saved settings to checkboxes
        var settings = loadSettings();
        cbRefresh.checked = settings.autoRefresh;
        cbClaim.checked   = settings.autoClaim;
    }

    // ── Entry point ──────────────────────────────────────────────────────────
    function init() {
        injectControls();

        var settings = loadSettings();
        if (settings.autoRefresh) startRefreshTimer();
        if (settings.autoClaim)   startClaimObserver();

        // Update elapsed time display every second
        setInterval(updateStatus, 1000);
    }

    // Wait for the existing index.html inline script to finish setting up
    // (it runs on DOMContentLoaded, so we wait for window load to be safe)
    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init);
    }
})();
```

- [ ] **Step 2: Manually verify the script has no syntax errors**

Open Terminal and run:

```bash
node --check /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/naviga-auto.js && echo "Syntax OK"
```
Expected: `Syntax OK`

---

### Task 2: Deliverable A — Write install.sh and uninstall.sh

**Files:**
- Create: `deliverable-a-cep-injector/install.sh`
- Create: `deliverable-a-cep-injector/uninstall.sh`

**Interfaces:**
- Consumes: `naviga-auto.js` (Task 1), original `index.html` at `/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html`
- Produces: Patched `index.html` with script tag; `naviga-auto.js` copied to extension's client folder

- [ ] **Step 1: Create install.sh**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/install.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

NAVIGA_CLIENT="/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../naviga-originals/client"

echo "=== Naviga Auto — Install ==="

# 1. Verify source files exist
if [ ! -f "$NAVIGA_CLIENT/index.html" ]; then
  echo "ERROR: Cannot find $NAVIGA_CLIENT/index.html"
  echo "Is the NavigaAd extension installed?"
  exit 1
fi

# 2. Check if already patched
if grep -q "naviga-auto.js" "$NAVIGA_CLIENT/index.html"; then
  echo "INFO: index.html already contains naviga-auto.js tag — skipping patch."
else
  # 3. Back up original index.html (if backup doesn't already exist from Task 0)
  mkdir -p "$BACKUP_DIR"
  if [ ! -f "$BACKUP_DIR/index.html" ]; then
    cp "$NAVIGA_CLIENT/index.html" "$BACKUP_DIR/index.html"
    echo "Backed up index.html to $BACKUP_DIR/index.html"
  fi

  # 4. Inject script tag before </body>
  sed -i.tmp 's|</body>|    <script type="text/javascript" src="naviga-auto.js"></script>\n</body>|' \
      "$NAVIGA_CLIENT/index.html"
  rm -f "$NAVIGA_CLIENT/index.html.tmp"
  echo "Patched index.html — added naviga-auto.js script tag"
fi

# 5. Copy naviga-auto.js to the extension client folder
cp "$SCRIPT_DIR/naviga-auto.js" "$NAVIGA_CLIENT/naviga-auto.js"
echo "Copied naviga-auto.js to $NAVIGA_CLIENT/"

echo ""
echo "=== Install complete ==="
echo "Restart Adobe InDesign for changes to take effect."
```

- [ ] **Step 2: Create uninstall.sh**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/uninstall.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

NAVIGA_CLIENT="/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../naviga-originals/client"

echo "=== Naviga Auto — Uninstall ==="

# 1. Restore original index.html from backup
if [ -f "$BACKUP_DIR/index.html" ]; then
  cp "$BACKUP_DIR/index.html" "$NAVIGA_CLIENT/index.html"
  echo "Restored original index.html from backup"
else
  echo "WARNING: No backup found at $BACKUP_DIR/index.html"
  echo "Attempting to remove script tag manually..."
  sed -i.tmp '/<script type="text\/javascript" src="naviga-auto.js"><\/script>/d' \
      "$NAVIGA_CLIENT/index.html"
  rm -f "$NAVIGA_CLIENT/index.html.tmp"
  echo "Removed naviga-auto.js script tag from index.html"
fi

# 2. Remove naviga-auto.js from extension folder
if [ -f "$NAVIGA_CLIENT/naviga-auto.js" ]; then
  rm "$NAVIGA_CLIENT/naviga-auto.js"
  echo "Removed naviga-auto.js from $NAVIGA_CLIENT/"
fi

echo ""
echo "=== Uninstall complete ==="
echo "Restart Adobe InDesign to restore original behavior."
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/install.sh
chmod +x /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/uninstall.sh
```

- [ ] **Step 4: Verify install.sh is valid bash**

```bash
bash -n /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/install.sh && echo "install.sh syntax OK"
bash -n /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/uninstall.sh && echo "uninstall.sh syntax OK"
```
Expected: two "syntax OK" lines.

---

### Task 3: Deliverable A — Write README and run install

**Files:**
- Create: `deliverable-a-cep-injector/README.md`

- [ ] **Step 1: Create README.md**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/README.md`:

```markdown
# Deliverable A — CEP Injector

Patches the NavigaAd CEP extension to auto-refresh the ad queue every 10 seconds
and optionally auto-claim unassigned ads.

## Files

- `naviga-auto.js` — the automation script
- `install.sh` — installs the patch (backs up originals first)
- `uninstall.sh` — fully reverses the patch
- `CHANGES.md` — detailed record of every change made to Naviga files

## Install

```bash
bash install.sh
```

Then restart Adobe InDesign.

## Use

After install, open the Naviga Ad Extension panel in InDesign. Two new checkboxes
appear below the Refresh/Logout buttons:

- **Auto-Refresh** (default ON) — refreshes the queue every 10 seconds while logged in
- **Auto-Claim** (default OFF) — instantly claims unassigned ads the moment they appear

Both settings are saved between sessions.

## Uninstall

```bash
bash uninstall.sh
```

Then restart Adobe InDesign. Naviga is fully restored to its original state.

## TOS Note

This deliverable modifies Naviga's installed extension files. See `CHANGES.md`
for the exact nature of every modification. Review with management and Naviga's
TOS before deploying in production.
```

- [ ] **Step 2: Run install.sh and verify it completes without errors**

```bash
bash /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/install.sh
```
Expected output:
```
=== Naviga Auto — Install ===
Patched index.html — added naviga-auto.js script tag
Copied naviga-auto.js to /Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/
=== Install complete ===
Restart Adobe InDesign for changes to take effect.
```

- [ ] **Step 3: Verify the patch was applied correctly**

```bash
grep -n "naviga-auto.js" "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html"
```
Expected: one line showing the script tag near the end of the file.

```bash
ls -la "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/naviga-auto.js"
```
Expected: file exists with a recent timestamp.

---

### Task 4: Deliverable B — Set up Python environment

**Files:**
- Create: `deliverable-b-menubar-app/requirements.txt`
- Create: `deliverable-b-menubar-app/README.md`

**Interfaces:**
- Produces: Python virtual environment at `deliverable-b-menubar-app/venv/` with rumps and pyobjc installed

- [ ] **Step 1: Create requirements.txt**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-b-menubar-app/requirements.txt`:

```
rumps>=0.4.0
pyobjc-framework-Cocoa>=10.0
pyobjc-framework-Quartz>=10.0
```

- [ ] **Step 2: Create and activate virtual environment, install dependencies**

```bash
cd /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-b-menubar-app
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```
Expected: pip installs rumps, pyobjc-framework-Cocoa, pyobjc-framework-Quartz without errors.

- [ ] **Step 3: Verify imports work**

```bash
/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-b-menubar-app/venv/bin/python3 -c "import rumps; import Cocoa; import Quartz; print('imports OK')"
```
Expected: `imports OK`

---

### Task 5: Deliverable B — Write naviga_helper.py

**Files:**
- Create: `deliverable-b-menubar-app/naviga_helper.py`

**Interfaces:**
- Consumes: `rumps`, `Cocoa` (pyobjc), `Quartz` (pyobjc)
- Produces: Runnable menu-bar app; `naviga_helper_settings.json` in the same directory for settings persistence

- [ ] **Step 1: Create naviga_helper.py**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-b-menubar-app/naviga_helper.py`:

```python
#!/usr/bin/env python3
"""
Naviga Ad Queue — macOS Menu Bar Helper (Deliverable B)
Clicks the Naviga panel's Refresh button inside InDesign on a timer.
Does not modify any Naviga files.
"""

import json
import os
import time
import threading
import subprocess

import rumps
import Quartz
import AppKit

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "naviga_helper_settings.json")
INDESIGN_BUNDLE = "com.adobe.InDesign"

DEFAULT_SETTINGS = {
    "auto_refresh": False,
    "auto_claim": False,
    "interval_seconds": 10,
}

INTERVAL_OPTIONS = [5, 10, 30, 60]


# ── Settings ─────────────────────────────────────────────────────────────────

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ── InDesign / Accessibility helpers ─────────────────────────────────────────

def indesign_is_frontmost():
    """Return True if InDesign is the currently active application."""
    active = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    return active.bundleIdentifier() == INDESIGN_BUNDLE


def get_indesign_pid():
    """Return InDesign's PID, or None if not running."""
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    for app in apps:
        if app.bundleIdentifier() == INDESIGN_BUNDLE:
            return app.processIdentifier()
    return None


def find_button_by_label_ax(pid, label):
    """
    Walk InDesign's AX tree looking for a button with the given label.
    Returns the AXUIElement if found, else None.
    CEP panels often don't expose HTML buttons in the AX tree — this is
    the primary attempt; coordinate fallback is used if this returns None.
    """
    app_ref = Quartz.AXUIElementCreateApplication(pid)

    def _search(element, depth=0):
        if depth > 12:
            return None
        role = _ax_attr(element, "AXRole")
        title = _ax_attr(element, "AXTitle") or _ax_attr(element, "AXDescription") or ""
        if role == "AXButton" and label.lower() in title.lower():
            return element
        children = _ax_attr(element, "AXChildren") or []
        for child in children:
            result = _search(child, depth + 1)
            if result is not None:
                return result
        return None

    return _search(app_ref)


def _ax_attr(element, attr):
    """Safely read an AX attribute, returning None on failure."""
    err, value = Quartz.AXUIElementCopyAttributeValue(element, attr, None)
    if err == 0:
        return value
    return None


def ax_press(element):
    """Send AXPress action to an AX element."""
    Quartz.AXUIElementPerformAction(element, "AXPress")


def get_indesign_window_frame(pid):
    """
    Return the (x, y, width, height) of InDesign's main window in screen
    coordinates (top-left origin), or None if not found.
    """
    app_ref = Quartz.AXUIElementCreateApplication(pid)
    windows = _ax_attr(app_ref, "AXWindows")
    if not windows:
        return None
    win = windows[0]
    pos_val  = _ax_attr(win, "AXPosition")
    size_val = _ax_attr(win, "AXSize")
    if pos_val is None or size_val is None:
        return None
    x, y = pos_val.x, pos_val.y
    w, h = size_val.width, size_val.height
    return (x, y, w, h)


def click_at_screen_coords(x, y):
    """
    Simulate a mouse click at absolute screen coordinates without
    activating/focusing the target application.
    Uses CGEvent so InDesign stays frontmost.
    """
    pt = Quartz.CGPointMake(x, y)
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)

    down = Quartz.CGEventCreateMouseEvent(src, Quartz.kCGEventLeftMouseDown, pt,
                                          Quartz.kCGMouseButtonLeft)
    up   = Quartz.CGEventCreateMouseEvent(src, Quartz.kCGEventLeftMouseUp,   pt,
                                          Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(0.05)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)


def click_naviga_refresh(pid):
    """
    Attempt to click the Refresh button.
    Strategy 1: AX tree lookup by label.
    Strategy 2: Coordinate estimate — Refresh button is in the top-right
                of the Naviga panel. Estimated offset from window right edge.
    Returns True if a click was attempted.
    """
    # Strategy 1: AX
    btn = find_button_by_label_ax(pid, "Refresh")
    if btn is not None:
        ax_press(btn)
        return True

    # Strategy 2: Coordinate fallback
    frame = get_indesign_window_frame(pid)
    if frame is None:
        return False
    x, y, w, h = frame
    # Refresh button sits ~115px from right edge, ~30px from top of window
    click_x = x + w - 115
    click_y = y + 30
    click_at_screen_coords(click_x, click_y)
    return True


def click_naviga_assign(pid):
    """
    Attempt to click 'Assign this to me' button.
    Strategy 1: AX tree lookup.
    Strategy 2: Not reliably coordinate-based (button position varies by
                queue content), so Strategy 1 only. Returns False if not found.
    """
    btn = find_button_by_label_ax(pid, "Assign this to me")
    if btn is not None:
        ax_press(btn)
        return True
    return False


# ── Menu Bar App ─────────────────────────────────────────────────────────────

class NavigaHelperApp(rumps.App):

    def __init__(self):
        super().__init__("N⚡", quit_button=None)
        self.settings = load_settings()
        self._timer_thread = None
        self._running = False
        self._last_refresh = None
        self._build_menu()
        if self.settings["auto_refresh"]:
            self._start_timer()

    def _build_menu(self):
        s = self.settings

        self._item_refresh = rumps.MenuItem(
            "Auto-Refresh: " + ("ON" if s["auto_refresh"] else "OFF"),
            callback=self._toggle_refresh
        )
        self._item_claim = rumps.MenuItem(
            "Auto-Claim: " + ("ON" if s["auto_claim"] else "OFF"),
            callback=self._toggle_claim
        )

        interval_menu = rumps.MenuItem("Interval")
        for secs in INTERVAL_OPTIONS:
            label = str(secs) + " seconds" + (" ✓" if secs == s["interval_seconds"] else "")
            interval_menu[label] = rumps.MenuItem(
                label, callback=self._make_interval_cb(secs)
            )
        self._item_interval = interval_menu

        self._item_status = rumps.MenuItem("Status: Idle")
        self._item_status.set_callback(None)

        self.menu = [
            self._item_refresh,
            self._item_claim,
            self._item_interval,
            None,
            self._item_status,
            None,
            rumps.MenuItem("Quit", callback=self._quit),
        ]

    def _make_interval_cb(self, secs):
        def cb(_):
            self.settings["interval_seconds"] = secs
            save_settings(self.settings)
            # Rebuild interval submenu to show checkmark
            self._rebuild_interval_menu()
            if self._running:
                self._start_timer()
        return cb

    def _rebuild_interval_menu(self):
        s = self.settings
        for secs in INTERVAL_OPTIONS:
            label_base = str(secs) + " seconds"
            label_check = label_base + " ✓"
            for key in list(self._item_interval.keys()):
                if label_base in key:
                    self._item_interval[key].title = (
                        label_check if secs == s["interval_seconds"] else label_base
                    )

    def _toggle_refresh(self, _):
        self.settings["auto_refresh"] = not self.settings["auto_refresh"]
        save_settings(self.settings)
        self._item_refresh.title = "Auto-Refresh: " + (
            "ON" if self.settings["auto_refresh"] else "OFF"
        )
        if self.settings["auto_refresh"]:
            self._start_timer()
        else:
            self._stop_timer()
            self._item_status.title = "Status: Idle"

    def _toggle_claim(self, _):
        self.settings["auto_claim"] = not self.settings["auto_claim"]
        save_settings(self.settings)
        self._item_claim.title = "Auto-Claim: " + (
            "ON" if self.settings["auto_claim"] else "OFF"
        )

    def _start_timer(self):
        self._stop_timer()
        self._running = True
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

    def _stop_timer(self):
        self._running = False

    def _timer_loop(self):
        while self._running:
            interval = self.settings["interval_seconds"]
            time.sleep(interval)
            if not self._running:
                break
            if not indesign_is_frontmost():
                self._item_status.title = "Status: Paused (InDesign not active)"
                continue
            pid = get_indesign_pid()
            if pid is None:
                self._item_status.title = "Status: InDesign not running"
                continue
            clicked = click_naviga_refresh(pid)
            if clicked:
                self._last_refresh = time.time()
                self._item_status.title = "Status: Refreshed just now"
                if self.settings["auto_claim"]:
                    time.sleep(1.5)
                    click_naviga_assign(pid)
            else:
                self._item_status.title = "Status: Could not find Refresh button"

    def _quit(self, _):
        self._stop_timer()
        rumps.quit_application()


if __name__ == "__main__":
    NavigaHelperApp().run()
```

- [ ] **Step 2: Verify syntax**

```bash
/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-b-menubar-app/venv/bin/python3 -m py_compile naviga_helper.py && echo "Syntax OK"
```
Expected: `Syntax OK`

---

### Task 6: Deliverable B — Write README and verify launch

**Files:**
- Create: `deliverable-b-menubar-app/README.md`

- [ ] **Step 1: Create README.md**

Create `/Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-b-menubar-app/README.md`:

```markdown
# Deliverable B — macOS Menu Bar Helper

A standalone menu-bar app that clicks the Naviga Ad Extension's Refresh button
inside Adobe InDesign on a configurable timer. Does not modify any Naviga files.

## Requirements

- macOS 12+
- Python 3.11+
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
```

- [ ] **Step 2: Do a dry-run import check (non-GUI)**

```bash
cd /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-b-menubar-app
venv/bin/python3 -c "
import json, os, time, threading
import rumps, Quartz, AppKit
from naviga_helper import load_settings, save_settings, indesign_is_frontmost, get_indesign_pid
print('All imports and top-level functions OK')
print('Default settings:', load_settings())
"
```
Expected: `All imports and top-level functions OK` followed by the default settings dict.

---

### Task 7: Final verification checklist

- [ ] **Step 1: Confirm backup files exist and are identical to source**

```bash
diff "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html" \
     /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/index.html \
  && echo "WARN: index.html backup matches patched version (install already ran)"
diff "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.js" \
     /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/index.js \
  && echo "index.js backup OK"
diff "/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/CSInterface.js" \
     /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/naviga-originals/client/CSInterface.js \
  && echo "CSInterface.js backup OK"
```

- [ ] **Step 2: Confirm final project structure**

```bash
find /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga -not -path "*/venv/*" -not -path "*/.git/*" | sort
```

Expected structure:
```
Naviga/
  deliverable-a-cep-injector/
    CHANGES.md
    install.sh
    naviga-auto.js
    README.md
    uninstall.sh
  deliverable-b-menubar-app/
    naviga_helper.py
    naviga_helper_settings.json  (created on first run)
    README.md
    requirements.txt
    venv/
  docs/
    superpowers/
      plans/
        2026-07-08-naviga-automation.md
      specs/
        2026-07-08-naviga-automation-design.md
  naviga-originals/
    client/
      CSInterface.js
      index.html
      index.js
```

- [ ] **Step 3: Test Deliverable A in InDesign**

1. Restart Adobe InDesign
2. Open Window > Extensions > Naviga Ad Extension
3. Log in if prompted
4. Verify two new checkboxes appear below Refresh/Logout buttons: "Auto-Refresh" and "Auto-Claim"
5. Verify "Auto-refresh: ON" status text appears
6. Wait 10 seconds — verify the queue refreshes automatically (loading indicator briefly appears)
7. Toggle Auto-Refresh OFF — verify timer stops

- [ ] **Step 4: Test Deliverable A uninstall**

```bash
bash /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/uninstall.sh
```
Restart InDesign and verify the extra checkboxes are gone and Naviga behaves normally.

- [ ] **Step 5: Re-install Deliverable A for ongoing use**

```bash
bash /Users/gabrielglenn/Projects/Claude-Code/Ballantine/Naviga/deliverable-a-cep-injector/install.sh
```
