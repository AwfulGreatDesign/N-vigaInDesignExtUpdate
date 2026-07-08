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
