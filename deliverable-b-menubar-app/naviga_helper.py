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

# Fallback presets still available via submenu for quick selection
INTERVAL_PRESETS = [5, 10, 30, 60, 99]


# ── Settings ──────────────────────────────────────────────────────────────────

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
                merged = {**DEFAULT_SETTINGS, **data}
                # Clamp interval to valid range
                secs = int(merged.get("interval_seconds", 10))
                merged["interval_seconds"] = max(1, min(99, secs))
                return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ── InDesign / Accessibility helpers ──────────────────────────────────────────

def indesign_is_frontmost():
    active = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    return active.bundleIdentifier() == INDESIGN_BUNDLE


def get_indesign_pid():
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    for app in apps:
        if app.bundleIdentifier() == INDESIGN_BUNDLE:
            return app.processIdentifier()
    return None


def _ax_attr(element, attr):
    err, value = Quartz.AXUIElementCopyAttributeValue(element, attr, None)
    if err == 0:
        return value
    return None


def find_button_by_label_ax(pid, label):
    """Walk InDesign's AX tree for a button whose title contains label."""
    app_ref = Quartz.AXUIElementCreateApplication(pid)

    def _search(element, depth=0):
        if depth > 12:
            return None
        role  = _ax_attr(element, "AXRole")
        title = _ax_attr(element, "AXTitle") or _ax_attr(element, "AXDescription") or ""
        if role == "AXButton" and label.lower() in title.lower():
            return element
        for child in (_ax_attr(element, "AXChildren") or []):
            result = _search(child, depth + 1)
            if result is not None:
                return result
        return None

    return _search(app_ref)


def ax_press(element):
    Quartz.AXUIElementPerformAction(element, "AXPress")


def get_indesign_window_frame(pid):
    app_ref  = Quartz.AXUIElementCreateApplication(pid)
    windows  = _ax_attr(app_ref, "AXWindows")
    if not windows:
        return None
    win      = windows[0]
    pos_val  = _ax_attr(win, "AXPosition")
    size_val = _ax_attr(win, "AXSize")
    if pos_val is None or size_val is None:
        return None
    return (pos_val.x, pos_val.y, size_val.width, size_val.height)


def click_at_screen_coords(x, y):
    """Simulate a left-click without stealing focus from InDesign."""
    pt  = Quartz.CGPointMake(x, y)
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
    Click the Refresh button.
    Strategy 1: AX tree lookup.
    Strategy 2: Coordinate fallback (~115px from right edge, ~30px from top of window).
    """
    btn = find_button_by_label_ax(pid, "Refresh")
    if btn is not None:
        ax_press(btn)
        return True

    frame = get_indesign_window_frame(pid)
    if frame is None:
        return False
    x, y, w, h = frame
    click_at_screen_coords(x + w - 115, y + 30)
    return True


def click_naviga_view(pid):
    """
    Click the first visible View button in the unassigned queue.
    Strategy 1: AX tree — looks for a button labelled 'View'.
    Strategy 2: Coordinate estimate — View button is the rightmost column of
                the first queue row (~115px from right, ~180px from top of window).
    Returns True if a click was attempted.
    """
    btn = find_button_by_label_ax(pid, "View")
    if btn is not None:
        ax_press(btn)
        return True

    # Coordinate fallback: approximate position of the first View button
    frame = get_indesign_window_frame(pid)
    if frame is None:
        return False
    x, y, w, h = frame
    click_at_screen_coords(x + w - 115, y + 180)
    return True


def click_naviga_assign(pid):
    """
    Click the 'Assign this to me' button in the detail view.
    AX tree only — button position varies with queue content so no coordinate fallback.
    Returns True if found and clicked.
    """
    btn = find_button_by_label_ax(pid, "Assign this to me")
    if btn is not None:
        ax_press(btn)
        return True
    return False


# ── Auto-claim: two-step workflow ─────────────────────────────────────────────
# Step 1 (called after refresh): click View on the first unassigned queue row.
# Step 2 (called after View opens detail): click Assign this to me.
# Both steps run on the timer thread with a 1.5 s gap to allow the detail
# panel to render before looking for the Assign button.

def run_auto_claim(pid, status_cb):
    """
    Execute the two-step claim workflow:
      1. Click View to open the ad detail panel.
      2. Wait for detail to render, then click Assign this to me.
    status_cb(msg) updates the menu bar status item.
    """
    status_cb("Status: Auto-claim — clicking View…")
    view_clicked = click_naviga_view(pid)
    if not view_clicked:
        status_cb("Status: Auto-claim — View button not found")
        return

    # Wait for the detail panel to render
    time.sleep(1.5)

    assigned = click_naviga_assign(pid)
    if assigned:
        status_cb("Status: Auto-claim — Assigned!")
    else:
        status_cb("Status: Auto-claim — Assign button not found (ad may be taken)")


# ── Menu Bar App ──────────────────────────────────────────────────────────────

class NavigaHelperApp(rumps.App):

    def __init__(self):
        super().__init__("N⚡", quit_button=None)
        self.settings = load_settings()
        self._timer_thread = None
        self._running = False
        self._build_menu()
        if self.settings["auto_refresh"]:
            self._start_timer()

    # ── Menu construction ─────────────────────────────────────────────────

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

        # Interval submenu — presets + custom entry
        interval_menu = rumps.MenuItem("Interval")
        for secs in INTERVAL_PRESETS:
            label = self._interval_label(secs)
            interval_menu[label] = rumps.MenuItem(label, callback=self._make_preset_cb(secs))
        interval_menu["Custom…"] = rumps.MenuItem("Custom…", callback=self._set_custom_interval)
        self._item_interval = interval_menu

        self._item_status = rumps.MenuItem(
            "Status: " + str(s["interval_seconds"]) + "s interval"
        )
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

    def _interval_label(self, secs):
        suffix = " ✓" if secs == self.settings["interval_seconds"] else ""
        return f"{secs} seconds{suffix}"

    # ── Interval controls ─────────────────────────────────────────────────

    def _make_preset_cb(self, secs):
        def cb(_):
            self._apply_interval(secs)
        return cb

    def _set_custom_interval(self, _):
        """Show a rumps input window for a 1–99 second custom interval."""
        window = rumps.Window(
            message="Enter refresh interval (1–99 seconds):",
            title="Set Interval",
            default_text=str(self.settings["interval_seconds"]),
            ok="Set",
            cancel="Cancel",
            dimensions=(100, 20),
        )
        response = window.run()
        if response.clicked:
            raw = response.text.strip()
            # Strip non-digits, take first two chars
            digits = ''.join(c for c in raw if c.isdigit())[:2]
            if digits:
                val = max(1, min(99, int(digits)))
                self._apply_interval(val)

    def _apply_interval(self, secs):
        self.settings["interval_seconds"] = secs
        save_settings(self.settings)
        self._rebuild_interval_menu()
        self._item_status.title = f"Status: {secs}s interval set"
        if self._running:
            self._start_timer()  # restart with new interval

    def _rebuild_interval_menu(self):
        for secs in INTERVAL_PRESETS:
            base  = f"{secs} seconds"
            check = f"{secs} seconds ✓"
            for key in list(self._item_interval.keys()):
                if key in (base, check):
                    self._item_interval[key].title = (
                        check if secs == self.settings["interval_seconds"] else base
                    )

    # ── Toggle callbacks ──────────────────────────────────────────────────

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

    # ── Timer ─────────────────────────────────────────────────────────────

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
            if not clicked:
                self._item_status.title = "Status: Could not find Refresh button"
                continue

            self._item_status.title = "Status: Refreshed just now"

            if self.settings["auto_claim"]:
                # Wait for API response to render new queue rows before looking for View
                time.sleep(1.5)
                if self._running:
                    run_auto_claim(pid, lambda msg: setattr(self._item_status, "title", msg))

    def _quit(self, _):
        self._stop_timer()
        rumps.quit_application()


if __name__ == "__main__":
    NavigaHelperApp().run()
