# Naviga Ad Queue Automation — Design Spec
**Date:** 2026-07-08  
**Status:** Approved  

---

## Problem Statement

Two designers share a Naviga Ad queue inside Adobe InDesign via the NavigaAd CEP extension (`/Library/Application Support/Adobe/CEP/extensions/NavigaAd/`). New ads enter the shared unassigned queue at unpredictable intervals. Manually clicking Refresh frequently causes missed ads and inefficiency. The goal is to automate:

1. **Phase 1:** Auto-refresh the queue every 10 seconds
2. **Phase 2:** Auto-claim ads from the unassigned queue the moment they appear

Two independent deliverables are built so management can evaluate technical approach and TOS risk before choosing one.

---

## Technical Context

- **Extension type:** Adobe CEP (Common Extensibility Platform) panel — HTML/CSS/JS running in embedded Chromium
- **Extension ID:** `com.naviga.ad.production`
- **Main panel file:** `/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client/index.html`
- **Refresh button:** `<button onclick="refresh();">Refresh</button>` — calls JS function `refresh()` which calls `login(false)` → `getMaterialLines()` → Naviga API
- **Assign button:** `<button id="assign-indd" onclick="assignArtist(materialId, artistId);">Assign this to me</button>` — appears in the DOM only when an unassigned ad is present
- **CSXS version:** 9.0 (InDesign 14–20 / CC 2024–2025)
- **Debug port:** Remote CEP debugger unavailable due to `--enable-nodejs` / `--mixed-context` flags in manifest

---

## Repository Structure

```
Naviga/
  deliverable-a-cep-injector/
    naviga-auto.js          ← patch script loaded by index.html
    install.sh              ← patches index.html, backs up original
    uninstall.sh            ← restores original index.html
    README.md
  deliverable-b-menubar-app/
    naviga_helper.py        ← macOS menu bar automation app
    requirements.txt        ← rumps, pyobjc
    README.md
  docs/
    superpowers/
      specs/
        2026-07-08-naviga-automation-design.md
```

---

## Deliverable A — CEP Injector

### Overview
A JavaScript file (`naviga-auto.js`) injected into the existing Naviga panel via a `<script>` tag added to `index.html`. Runs inside the panel's own Chromium context with direct access to all existing JS functions.

### Installation
`install.sh` backs up `index.html` to `index.html.backup`, then appends one `<script src="naviga-auto.js">` tag before `</body>`. `uninstall.sh` restores the backup.

### Phase 1 — Auto-Refresh
- `setInterval` fires every `AUTO_REFRESH_INTERVAL` (default: 10000ms)
- Before each tick: checks `$('#divLogout').is(':visible')` — skips if user is not logged in
- Calls `refresh()` directly (the existing function in the page)
- Injects a small status line next to the Refresh button: `"Auto-refresh ON — last: 0:08 ago"`
- Status line styled to match existing panel aesthetics (gray, small font)

### Phase 2 — Auto-Claim
- `MutationObserver` watches `#tblProjectLinesUnAssigned tbody` for DOM changes
- On mutation: scans for any `button[id="assign-indd"]` element
- If found: clicks it immediately (fires `assignArtist()`)
- Observer is only active when Auto-Claim toggle is ON

### UI Controls
Two checkboxes injected into the panel next to the Refresh/Logout buttons:
- `[ ] Auto-Refresh` (default: ON)
- `[ ] Auto-Claim` (default: OFF — requires deliberate opt-in)

Settings stored in `localStorage` under keys `naviga_auto_refresh` and `naviga_auto_claim` — survive panel reloads.

### Constants (editable at top of naviga-auto.js)
```js
const AUTO_REFRESH_INTERVAL = 10000;  // ms
const CLAIM_DELAY_MS = 0;             // delay before auto-claiming (0 = immediate)
```

### TOS Risk
**Higher.** Modifies Naviga's installed extension files on disk. Naviga could argue unauthorized modification. Any Naviga software update will overwrite `index.html` and the patch must be re-applied. API call rate increases proportionally to refresh interval.

---

## Deliverable B — Menu Bar Helper

### Overview
A standalone macOS menu-bar app written in Python using `rumps` (menu bar framework) and `pyobjc` (macOS Accessibility APIs). Sits in the Mac menu bar as an icon. Clicks the Naviga panel's Refresh button on a timer using macOS system-level input simulation — no modification of Naviga files.

### Menu Structure
```
N⚡
├── Auto-Refresh: OFF        ← toggle
├── Auto-Claim: OFF          ← toggle
├── Interval: 10 seconds  ►  ← submenu: 5s / 10s / 30s / 60s
├── ─────────────────
├── Status: Idle
└── Quit
```

### Click Strategy (in priority order)
1. **AX Tree approach:** Use `AXUIElement` to walk InDesign's accessibility tree → find the Naviga panel's web content → find button with AX label "Refresh" → send `AXPress` action
2. **Coordinate fallback:** If AX tree does not expose the button (common in CEP Chromium iframes), calculate pixel position of the Refresh button relative to the InDesign window frame and use `CGEventCreateMouseEvent` to click — without activating/focusing InDesign

### Focus Safety
- On each tick: checks that InDesign (`com.adobe.InDesign`) is the frontmost application
- If user has switched to another app: pauses the timer, resumes when InDesign regains focus
- Never calls `NSApp.activateIgnoringOtherApps` — focus is never stolen

### Phase 2 — Auto-Claim
Since the helper has no DOM access:
- After each Refresh click, waits `CLAIM_SCAN_DELAY` (default: 1500ms) for API response to render
- Scans AX tree (or pixel region) for a button labeled "Assign this to me"
- If found: clicks it

### Requirements
```
rumps>=0.4.0
pyobjc-framework-Cocoa>=10.0
pyobjc-framework-Quartz>=10.0
```

### TOS Risk
**Lower.** Does not modify any Naviga files. Simulates human UI interaction at the OS level — legally comparable to a user clicking faster. No direct API calls. The key TOS question is whether automated UI interaction with a licensed product is permitted — most SaaS agreements are silent on this.

---

## TOS Risk Summary for Management

| | Deliverable A (CEP Injector) | Deliverable B (Menu Bar) |
|---|---|---|
| Modifies Naviga files | YES | No |
| Direct API calls | YES (via refresh()) | No (clicks UI only) |
| Survives Naviga updates | No (must re-patch) | Yes |
| Technical reliability | Very high | High (with AX fallback) |
| TOS risk | Higher | Lower |
| Build complexity | Low | Medium |

**Recommendation for management:** Deliverable B is the safer TOS path. Deliverable A is simpler and more reliable technically. Both achieve identical business outcomes.

---

## Out of Scope
- Modifying the Naviga server or API
- Automating any action beyond Refresh and Assign-to-me
- Multi-machine or multi-user deployment
- Notification/alerting when ads are claimed by the other designer
