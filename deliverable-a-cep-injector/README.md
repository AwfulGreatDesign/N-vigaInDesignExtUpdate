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
